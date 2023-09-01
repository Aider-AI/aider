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

    def commit(self, fnames=None, context=None, prefix=None, message=None):
        if not fnames and not self.repo.is_dirty():
            return

        if message:
            commit_message = message
        else:
            diffs = self.get_diffs(fnames)
            commit_message = self.get_commit_message(diffs, context)

        if not commit_message:
            commit_message = "(no commit message provided)"

        if prefix:
            commit_message = prefix + commit_message

        full_commit_message = commit_message
        if context:
            full_commit_message += "\n\n# Aider chat conversation:\n\n" + context

        cmd = ["-m", full_commit_message, "--no-verify"]
        if fnames:
            fnames = [str(self.abs_root_path(fn)) for fn in fnames]
            for fname in fnames:
                self.repo.git.add(fname)
            cmd += ["--"] + fnames
        else:
            cmd += ["-a"]

        self.repo.git.commit(cmd)
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

        for model in models.Model.commit_message_models():
            commit_message = simple_send_with_retries(model.name, messages)
            if commit_message:
                break

        if not commit_message:
            self.io.tool_error("Failed to generate commit message!")
            return

        commit_message = commit_message.strip()
        if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
            commit_message = commit_message[1:-1].strip()

        return commit_message

    def get_diffs(self, fnames=None):
        # We always want diffs of index and working dir
        try:
            commits = self.repo.iter_commits(self.repo.active_branch)
            current_branch_has_commits = any(commits)
        except git.exc.GitCommandError:
            current_branch_has_commits = False

        if not fnames:
            fnames = []

        diffs = ""
        for fname in fnames:
            if not self.path_in_repo(fname):
                diffs += f"Added {fname}\n"

        if current_branch_has_commits:
            args = ["HEAD", "--"] + list(fnames)
            diffs += self.repo.git.diff(*args)
            return diffs

        wd_args = ["--"] + list(fnames)
        index_args = ["--cached"] + wd_args

        diffs += self.repo.git.diff(*index_args)
        diffs += self.repo.git.diff(*wd_args)

        return diffs

    def diff_commits(self, pretty, from_commit, to_commit):
        args = []
        if pretty:
            args += ["--color"]

        args += [from_commit, to_commit]
        diffs = self.repo.git.diff(*args)

        return diffs

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
        res = set(
            str(Path(PurePosixPath((Path(self.root) / path).relative_to(self.root))))
            for path in files
        )

        return res

    def path_in_repo(self, path):
        if not self.repo:
            return

        tracked_files = set(self.get_tracked_files())
        return path in tracked_files

    def abs_root_path(self, path):
        res = Path(self.root) / path
        return utils.safe_abs_path(res)

    def is_dirty(self, path=None):
        if path and not self.path_in_repo(path):
            return True

        return self.repo.is_dirty(path=path)
