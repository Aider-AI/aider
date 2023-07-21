import os
from pathlib import Path, PurePosixPath

import git
import openai

from aider import models, prompts, utils
from aider.sendchat import send_with_retries


class AiderRepo:
    repo = None

    def __init__(self, io, cmd_line_fnames):
        self.io = io

        if not cmd_line_fnames:
            cmd_line_fnames = ["."]

        repo_paths = []
        for fname in cmd_line_fnames:
            fname = Path(fname)
            if not fname.exists():
                self.io.tool_output(f"Creating empty file {fname}")
                fname.parent.mkdir(parents=True, exist_ok=True)
                fname.touch()

            fname = fname.resolve()

            try:
                repo_path = git.Repo(fname, search_parent_directories=True).working_dir
                repo_path = utils.safe_abs_path(repo_path)
                repo_paths.append(repo_path)
            except git.exc.InvalidGitRepositoryError:
                pass

            if fname.is_dir():
                continue

        num_repos = len(set(repo_paths))

        if num_repos == 0:
            raise FileNotFoundError
        if num_repos > 1:
            self.io.tool_error("Files are in different git repos.")
            raise FileNotFoundError

        # https://github.com/gitpython-developers/GitPython/issues/427
        self.repo = git.Repo(repo_paths.pop(), odbt=git.GitDB)
        self.root = utils.safe_abs_path(self.repo.working_tree_dir)

    def ___(self, fnames):

        # TODO!

        self.abs_fnames.add(str(fname))

        new_files = []
        for fname in fnames:
            relative_fname = self.get_rel_fname(fname)

            tracked_files = set(self.get_tracked_files())
            if relative_fname not in tracked_files:
                new_files.append(relative_fname)

        if new_files:
            rel_repo_dir = self.get_rel_repo_dir()

            self.io.tool_output(f"Files not tracked in {rel_repo_dir}:")
            for fn in new_files:
                self.io.tool_output(f" - {fn}")
            if self.io.confirm_ask("Add them?"):
                for relative_fname in new_files:
                    self.repo.git.add(relative_fname)
                    self.io.tool_output(f"Added {relative_fname} to the git repo")
                show_files = ", ".join(new_files)
                commit_message = f"Added new files to the git repo: {show_files}"
                self.repo.git.commit("-m", commit_message, "--no-verify")
                commit_hash = self.repo.head.commit.hexsha[:7]
                self.io.tool_output(f"Commit {commit_hash} {commit_message}")
            else:
                self.io.tool_error("Skipped adding new files to the git repo.")

    def commit(
        self, context=None, prefix=None, ask=False, message=None, which="chat_files", pretty=False
    ):

        ## TODO!

        repo = self.repo
        if not repo:
            return

        if not repo.is_dirty():
            return

        def get_dirty_files_and_diffs(file_list):
            diffs = ""
            relative_dirty_files = []
            for fname in file_list:
                relative_fname = self.get_rel_fname(fname)
                relative_dirty_files.append(relative_fname)

                try:
                    current_branch_commit_count = len(
                        list(self.repo.iter_commits(self.repo.active_branch))
                    )
                except git.exc.GitCommandError:
                    current_branch_commit_count = None

                if not current_branch_commit_count:
                    continue

                these_diffs = self.get_diffs(pretty, "HEAD", "--", relative_fname)

                if these_diffs:
                    diffs += these_diffs + "\n"

            return relative_dirty_files, diffs

        if which == "repo_files":
            all_files = [os.path.join(self.root, f) for f in self.get_all_relative_files()]
            relative_dirty_fnames, diffs = get_dirty_files_and_diffs(all_files)
        elif which == "chat_files":
            relative_dirty_fnames, diffs = get_dirty_files_and_diffs(self.abs_fnames)
        else:
            raise ValueError(f"Invalid value for 'which': {which}")

        if self.show_diffs or ask:
            # don't use io.tool_output() because we don't want to log or further colorize
            print(diffs)

        if message:
            commit_message = message
        else:
            commit_message = self.get_commit_message(diffs, context)

        if not commit_message:
            commit_message = "work in progress"

        if prefix:
            commit_message = prefix + commit_message

        if ask:
            if which == "repo_files":
                self.io.tool_output("Git repo has uncommitted changes.")
            else:
                self.io.tool_output("Files have uncommitted changes.")

            res = self.io.prompt_ask(
                "Commit before the chat proceeds [y/n/commit message]?",
                default=commit_message,
            ).strip()
            self.last_asked_for_commit_time = self.get_last_modified()

            self.io.tool_output()

            if res.lower() in ["n", "no"]:
                self.io.tool_error("Skipped commmit.")
                return
            if res.lower() not in ["y", "yes"] and res:
                commit_message = res

        repo.git.add(*relative_dirty_fnames)

        full_commit_message = commit_message + "\n\n# Aider chat conversation:\n\n" + context
        repo.git.commit("-m", full_commit_message, "--no-verify")
        commit_hash = repo.head.commit.hexsha[:7]
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

        messages = [
            dict(role="system", content=prompts.commit_system),
            dict(role="user", content=context + diffs),
        ]

        try:
            _hash, response = send_with_retries(
                model=models.GPT35.name,
                messages=messages,
                functions=None,
                stream=False,
            )
            commit_message = completion.choices[0].message.content
        except (AttributeError, openai.error.InvalidRequestError):
            self.io.tool_error(f"Failed to generate commit message using {models.GPT35.name}")
            return

        commit_message = commit_message.strip()
        if commit_message and commit_message[0] == '"' and commit_message[-1] == '"':
            commit_message = commit_message[1:-1].strip()

        return commit_message

    def get_diffs(self, pretty, *args):
        if pretty:
            args = ["--color"] + list(args)

        diffs = self.repo.git.diff(*args)
        return diffs

    def get_tracked_files(self):
        if not self.repo:
            return []

        try:
            commit = self.repo.head.commit
        except ValueError:
            return set()

        files = []
        for blob in commit.tree.traverse():
            if blob.type == "blob":  # blob is a file
                files.append(blob.path)

        # convert to appropriate os.sep, since git always normalizes to /
        res = set(str(Path(PurePosixPath(path))) for path in files)

        return res
