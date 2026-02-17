import contextlib
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

import pathspec

from aider.vcs.common import get_commit_message
from aider.vcs.git import set_git_env

ANY_JJ_ERROR = (subprocess.CalledProcessError, FileNotFoundError)


class JjVCS:
    name = "JJ"
    git_repo_error = None # unused, for compatibility

    def __init__(
        self,
        io,
        fnames,
        git_dname,  # unused, for compatibility
        models=None,
        attribute_author=True,
        attribute_committer=True,
        attribute_commit_message_author=False,
        attribute_commit_message_committer=False,
        commit_prompt=None,
        git_commit_verify=False,  # unused, for compatibility
        attribute_co_authored_by=False,
    ):
        self.io = io
        self.models = models
        self.commit_prompt = commit_prompt
        self.attribute_author = attribute_author
        self.attribute_co_authored_by = attribute_co_authored_by

        if git_dname:
            check_fnames = [git_dname]
        elif fnames:
            check_fnames = fnames
        else:
            check_fnames = ["."]

        repo_root = None
        for fname in check_fnames:
            path = Path(fname).resolve()
            if not path.exists() and path.parent.exists():
                path = path.parent

            try:
                res = subprocess.run(
                    ["jj", "root"],
                    cwd=str(path),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                current_root = res.stdout.strip()
                if repo_root is None:
                    repo_root = current_root
                elif repo_root != current_root:
                    self.io.tool_error("Files are in different JJ repos.")
                    raise FileNotFoundError
            except ANY_JJ_ERROR:
                continue

        if repo_root is None:
            raise FileNotFoundError

        self._root = repo_root
        self.normalized_path = {}

    @property
    def root(self):
        return self._root

    def _run(self, *args, **kwargs):
        return subprocess.run(
            ["jj"] + list(args),
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            **kwargs,
        )

    @staticmethod
    def is_repo(path):
        try:
            res = subprocess.run(
                ["jj", "root"],
                cwd=path,
                capture_output=True,
                text=True,
                check=True,
            )
            return res.stdout.strip()
        except ANY_JJ_ERROR:
            return None

    def add(self, fnames):
        if not isinstance(fnames, list):
            fnames = [fnames]

        for fname in fnames:
            try:
                self._run("file", "track", fname, check=True)
            except subprocess.CalledProcessError as e:
                self.io.tool_error(f"Unable to track {fname}: {e.stderr}")

    def commit(
        self, fnames=None, context=None, message=None, aider_edits=False, coder=None
    ):
        if not self.is_dirty():
            return

        diffs = self.get_diffs(fnames)
        if not diffs:
            return

        if message:
            commit_message = message
        else:
            user_language = None
            if coder:
                user_language = coder.commit_language
                if not user_language:
                    user_language = coder.get_user_language()
            commit_message = get_commit_message(
                self.io, self.models, self.commit_prompt, diffs, context, user_language
            )

        if not commit_message:
            commit_message = "(no commit message provided)"

        if coder and hasattr(coder, "args"):
            attribute_author = coder.args.attribute_author
            attribute_co_authored_by = coder.args.attribute_co_authored_by
        else:
            attribute_author = self.attribute_author
            attribute_co_authored_by = self.attribute_co_authored_by

        author_explicit = attribute_author is not None
        effective_author = True if attribute_author is None else attribute_author

        commit_message_trailer = ""
        if aider_edits and attribute_co_authored_by:
            model_name = "unknown-model"
            if coder and hasattr(coder, "main_model") and coder.main_model.name:
                model_name = coder.main_model.name
            commit_message_trailer = (
                f"\n\nCo-authored-by: aider ({model_name}) <aider@aider.chat>"
            )

        use_attribute_author = (
            aider_edits
            and effective_author
            and (not attribute_co_authored_by or author_explicit)
        )

        full_commit_message = commit_message + commit_message_trailer
        try:
            original_author_name_env = os.environ.get("GIT_AUTHOR_NAME")
            original_user_name_res = self._run("config", "get", "user.name")
            original_user_name = original_user_name_res.stdout.strip()
            committer_name = f"{original_user_name} (aider)"

            with contextlib.ExitStack() as stack:
                if use_attribute_author:
                    stack.enter_context(
                        set_git_env(
                            "GIT_AUTHOR_NAME", committer_name, original_author_name_env
                        )
                    )

                cmd = ["commit", "-m", full_commit_message]
                if fnames:
                    cmd.extend(fnames)
                res = self._run(*cmd, check=True)

            commit_output = res.stderr
            commit_hash = None

            for line in commit_output.splitlines():
                match = re.search(r"Parent commit \(@-\)\s+:\s+\S+\s+(\S+)", line)
                if match:
                    commit_hash = match.group(1)
                    break

            if not commit_hash:
                # Retrieve from log if parsing failed
                res = self._run(
                    "log", "--no-graph", "-r", "@-", "-T", "commit_id.short(8)"
                )
                commit_hash = res.stdout.strip()

            self.io.tool_output(f"Commit {commit_hash} {commit_message}", bold=True)
            return commit_hash, commit_message

        except subprocess.CalledProcessError as e:
            self.io.tool_error(f"Unable to commit: {e.stderr}")

    def get_diffs(self, fnames=None):
        args = ["diff"]
        if fnames:
            args.extend(fnames)
        else:
            args.append("--git")
        res = self._run(*args)
        return res.stdout

    def diff_commits(self, pretty, from_commit, to_commit):
        args = ["diff", f"--from={from_commit}", f"--to={to_commit}"]
        res = self._run(*args)
        return res.stdout

    def get_tracked_files(self):
        res = self._run("file", "list")
        if res.returncode != 0:
            return []

        files = res.stdout.splitlines()
        return files

    def is_ignored(self, path):
        path_obj = Path(path)
        if not path_obj.is_absolute():
            path_obj = Path(self.root) / path_obj
        path_obj = path_obj.resolve()

        try:
            relative_path_obj = path_obj.relative_to(self.root)
        except ValueError:
            return False

        # Git precedence rules:
        # 1. Last matching pattern in a file wins.
        # 2. Patterns in deeper .gitignore files override parent dirs.
        # 3. If a directory is excluded, files inside it cannot be re-included.

        # Check parent directories first for exclusion.
        for i in range(len(relative_path_obj.parts)):
            # Don't check the file itself, just parent dirs
            parent_dir_rel = Path(*relative_path_obj.parts[:i])
            if str(parent_dir_rel) == ".":
                continue

            match = self._get_final_match(parent_dir_rel)
            if match and not match.startswith("!"):
                return True  # An ancestor dir is ignored, so this file is ignored.

        # Now check the file itself
        match = self._get_final_match(relative_path_obj)
        if match and not match.startswith("!"):
            return True

        return False

    def _get_final_match(self, relative_path):
        """
        relative_path is relative to repo root.
        Returns the last matching pattern string, or None.
        """
        last_match = None

        # Walk from root down to file path
        dirs_to_check = [Path(self.root)]
        current_prefix = Path(self.root)

        path_parts = relative_path.parts

        for part in path_parts[:-1]:
            current_prefix = current_prefix / part
            dirs_to_check.append(current_prefix)

        for gitignore_dir in dirs_to_check:
            gitignore_path = gitignore_dir / ".gitignore"
            if not gitignore_path.is_file():
                continue

            with gitignore_path.open(encoding="utf-8", errors="ignore") as f:
                lines = f.read().splitlines()

            try:
                path_for_spec = relative_path.relative_to(
                    gitignore_dir.relative_to(self.root)
                )
            except ValueError:
                continue

            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                spec = pathspec.PathSpec.from_lines(
                    pathspec.patterns.GitWildMatchPattern, [line]
                )
                if spec.match_file(str(path_for_spec)):
                    last_match = line

        return last_match

    def path_in_repo(self, path):
        return path in self.get_tracked_files()

    def is_dirty(self, path=None):
        args = ["status"]
        if path:
            args.append(path)
        res = self._run(*args)
        output = res.stdout
        if not output.strip():
            return False
        return "The working copy has no changes." not in output

    def get_dirty_files(self):
        res = self._run("status")
        files = []
        for line in res.stdout.splitlines():
            # Example lines:
            # Working copy changes:
            # M aider/main.py
            # A aider/vcs/jj.py
            if line.startswith("Working copy") or line.startswith("Parent commit"):
                continue
            parts = line.split()
            if len(parts) > 1:
                files.append(parts[-1])
        return files

    def get_head_commit_sha(self, short=False):
        template = "commit_id"
        if short:
            template += ".short(8)"
        res = self._run("log", "--no-graph", "-r", "@", "-T", template)
        return res.stdout.strip()

    def get_head_commit_message(self, default=None):
        res = self._run("log", "--no-graph", "-r", "@", "-T", "description")
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        return default

    def undo_last_commit(self, aider_commit_hashes):
        res = self._run("log", "--no-graph", "-r", "@-", "-T", "commit_id.short(8)")
        prev_commit_hash = res.stdout.strip()
        if prev_commit_hash not in aider_commit_hashes:
            self.io.tool_error(
                "The last commit was not made by aider in this chat session."
            )
            return

        try:
            res_id = self._run(
                "log", "--no-graph", "-r", "@-", "-T", "commit_id"
            ).stdout.strip()
            self._run("abandon", res_id, check=True)
            self.io.tool_output(f"Abandoned commit {prev_commit_hash}")
            return True
        except subprocess.CalledProcessError as e:
            self.io.tool_error(f"Unable to undo: {e.stderr}")

    def get_rel_repo_dir(self):
        try:
            return os.path.relpath(Path(self.root) / ".jj", os.getcwd())
        except (ValueError, OSError):
            return str(Path(self.root) / ".jj")

    def normalize_path(self, path):
        orig_path = path
        res = self.normalized_path.get(orig_path)
        if res:
            return res

        path = str(Path(PurePosixPath((Path(self.root) / path).relative_to(self.root))))
        self.normalized_path[orig_path] = path
        return path
