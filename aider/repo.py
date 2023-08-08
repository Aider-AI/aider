import os
from pathlib import Path, PurePosixPath

import git

from aider import models, prompts, utils
from aider.sendchat import simple_send_with_retries

from .dump import dump  # noqa: F401


class GitRepo:
    repo = None

    def __init__(self, io, fnames, git_dname):
        self.io = io

        if git_dname:
            check_fnames = [git_dname]
        elif fnames:
            check_fnames = fnames
        else:
            check_fnames = ["."]

        repo_paths = []
        for fname in check_fnames:
            fname = Path(fname)
            fname = fname.resolve()

            if not fname.exists() and fname.parent.exists():
                fname = fname.parent

            try:
                repo_path = git.Repo(fname, search_parent_directories=True).working_dir
                repo_path = utils.safe_abs_path(repo_path)
                repo_paths.append(repo_path)
            except git.exc.InvalidGitRepositoryError:
                pass

        num_repos = len(set(repo_paths))

        if num_repos == 0:
            raise FileNotFoundError
        if num_repos > 1:
            self.io.tool_error("Files are in different git repos.")
            raise FileNotFoundError

        # https://github.com/gitpython-developers/GitPython/issues/427
        self.repo = git.Repo(repo_paths.pop(), odbt=git.GitDB)
        self.root = utils.safe_abs_path(self.repo.working_tree_dir)

    def add_new_files(self, fnames):
        cur_files = [Path(fn).resolve() for fn in self.get_tracked_files()]
        for fname in fnames:
            if Path(fname).resolve() in cur_files:
                continue
            if not Path(fname).exists():
                continue
            self.io.tool_output(f"Adding {fname} to git")
            self.repo.git.add(fname)

    def commit(self, context=None, prefix=None, message=None):
        if not self.repo.is_dirty():
            return

        if message:
            commit_message = message
        else:
            diffs = self.get_diffs(False)
            commit_message = self.get_commit_message(diffs, context)

        if not commit_message:
            commit_message = "(no commit message provided)"

        if prefix:
            commit_message = prefix + commit_message

        full_commit_message = commit_message
        if context:
            full_commit_message += "\n\n# Aider chat conversation:\n\n" + context

        self.repo.git.commit("-a", "-m", full_commit_message, "--no-verify")
        commit_hash = self.repo.head.commit.hexsha[:7]
        self.io.tool_output(f"Commit {commit_hash} {commit_message}")

        return commit_hash, commit_message

    def get_rel_repo_dir(self):
        try:
            return os.path.relpath(self.repo.git_dir, os.getcwd())
        except ValueError:
            return self.repo.git_dir

    def get_commit_message(self, diffs, context):
        if len(diffs) >= 4 * 1024 * 4:
            self.io.tool_error(
                f"Diff is too large for {models.GPT35.name} to generate a commit message."
            )
            return

        diffs = "# Diffs:\n" + diffs

        content = ""
        if context:
            content += context + "\n"
        content += diffs

        messages = [
            dict(role="system", content=prompts.commit_system),
            dict(role="user", content=content),
        ]

        for model in [models.GPT35.name, models.GPT35_16k.name]:
            commit_message = simple_send_with_retries(model, messages)
            if commit_message:
                break

        if not commit_message:
            self.io.tool_error("Failed to generate commit message!")
            return

        commit_message = commit_message.strip()
        if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
            commit_message = commit_message[1:-1].strip()

        return commit_message

    def get_diffs(self, pretty, *args):
        # we always want diffs of working-dir + index versus repo
        args = ["--cached"] + list(args)

        if pretty:
            args = ["--color"] + list(args)

        diffs = self.repo.git.diff(*args)
        return diffs

    def show_diffs(self, pretty):
        diffs = self.get_diffs(pretty)
        print(diffs)

    def get_tracked_files(self):
        if not self.repo:
            return []

        try:
            commit = self.repo.head.commit
        except ValueError:
            commit = None

        files = []
        if commit:
            for blob in commit.tree.traverse():
                if blob.type == "blob":  # blob is a file
                    files.append(blob.path)

        # Add staged files
        index = self.repo.index
        staged_files = [path for path, _ in index.entries.keys()]

        files.extend(staged_files)

        # convert to appropriate os.sep, since git always normalizes to /
        res = set(str(Path(PurePosixPath(path))) for path in files)

        return res

    def is_dirty(self):
        return self.repo.is_dirty()
