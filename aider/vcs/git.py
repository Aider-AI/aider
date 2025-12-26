import contextlib
import os
from pathlib import Path, PurePosixPath

try:
    import git

    ANY_GIT_ERROR = [
        git.exc.ODBError,
        git.exc.GitError,
        git.exc.InvalidGitRepositoryError,
        git.exc.GitCommandNotFound,
    ]
except ImportError:
    git = None
    ANY_GIT_ERROR = []

from aider import utils
from aider.vcs.common import get_commit_message

ANY_GIT_ERROR += [
    OSError,
    IndexError,
    BufferError,
    TypeError,
    ValueError,
    AttributeError,
    AssertionError,
    TimeoutError,
]
ANY_GIT_ERROR = tuple(ANY_GIT_ERROR)


@contextlib.contextmanager
def set_git_env(var_name, value, original_value):
    """Temporarily set a Git environment variable."""
    os.environ[var_name] = value
    try:
        yield
    finally:
        if original_value is not None:
            os.environ[var_name] = original_value
        elif var_name in os.environ:
            del os.environ[var_name]


class GitVCS:
    repo = None
    git_repo_error = None
    name = "Git"

    def __init__(
        self,
        io,
        fnames,
        git_dname,
        models=None,
        attribute_author=True,
        attribute_committer=True,
        attribute_commit_message_author=False,
        attribute_commit_message_committer=False,
        commit_prompt=None,
        git_commit_verify=True,
        attribute_co_authored_by=False,  # Added parameter
    ):
        self.io = io
        self.models = models

        self.normalized_path = {}
        self.tree_files = {}

        self.attribute_author = attribute_author
        self.attribute_committer = attribute_committer
        self.attribute_commit_message_author = attribute_commit_message_author
        self.attribute_commit_message_committer = attribute_commit_message_committer
        self.attribute_co_authored_by = (
            attribute_co_authored_by  # Assign from parameter
        )
        self.commit_prompt = commit_prompt
        self.git_commit_verify = git_commit_verify

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
            except ANY_GIT_ERROR:
                pass

        num_repos = len(set(repo_paths))

        if num_repos == 0:
            raise FileNotFoundError
        if num_repos > 1:
            self.io.tool_error("Files are in different git repos.")
            raise FileNotFoundError

        # https://github.com/gitpython-developers/GitPython/issues/427
        self.repo = git.Repo(repo_paths.pop(), odbt=git.GitDB)
        self._root = utils.safe_abs_path(self.repo.working_tree_dir)

    @property
    def root(self):
        return self._root

    @staticmethod
    def is_repo(path):
        if not git:
            return None
        try:
            repo = git.Repo(path, search_parent_directories=True)
            return repo.working_tree_dir
        except ANY_GIT_ERROR:
            return None

    def add(self, fnames):
        if not isinstance(fnames, list):
            fnames = [fnames]
        fnames = [str(Path(self.root) / fn) for fn in fnames]
        for fname in fnames:
            try:
                self.repo.git.add(fname)
            except ANY_GIT_ERROR as err:
                self.io.tool_error(f"Unable to add {fname}: {err}")

    def commit(
        self, fnames=None, context=None, message=None, aider_edits=False, coder=None
    ):
        if not fnames and not self.repo.is_dirty():
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

        if coder and hasattr(coder, "args"):
            attribute_author = coder.args.attribute_author
            attribute_committer = coder.args.attribute_committer
            attribute_commit_message_author = coder.args.attribute_commit_message_author
            attribute_commit_message_committer = (
                coder.args.attribute_commit_message_committer
            )
            attribute_co_authored_by = coder.args.attribute_co_authored_by
        else:
            attribute_author = self.attribute_author
            attribute_committer = self.attribute_committer
            attribute_commit_message_author = self.attribute_commit_message_author
            attribute_commit_message_committer = self.attribute_commit_message_committer
            attribute_co_authored_by = self.attribute_co_authored_by

        author_explicit = attribute_author is not None
        committer_explicit = attribute_committer is not None

        effective_author = True if attribute_author is None else attribute_author
        effective_committer = (
            True if attribute_committer is None else attribute_committer
        )

        prefix_commit_message = aider_edits and (
            attribute_commit_message_author or attribute_commit_message_committer
        )

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

        use_attribute_committer = effective_committer and (
            not (aider_edits and attribute_co_authored_by) or committer_explicit
        )

        if not commit_message:
            commit_message = "(no commit message provided)"

        if prefix_commit_message:
            commit_message = "aider: " + commit_message

        full_commit_message = commit_message + commit_message_trailer

        cmd = ["-m", full_commit_message]
        if not self.git_commit_verify:
            cmd.append("--no-verify")
        if fnames:
            self.add(fnames)
            fnames_abs = [str(Path(self.root) / fn) for fn in fnames]
            cmd += ["--"] + fnames_abs
        else:
            cmd += ["-a"]

        original_user_name = self.repo.git.config("--get", "user.name")
        original_committer_name_env = os.environ.get("GIT_COMMITTER_NAME")
        original_author_name_env = os.environ.get("GIT_AUTHOR_NAME")
        committer_name = f"{original_user_name} (aider)"

        try:
            with contextlib.ExitStack() as stack:
                if use_attribute_committer:
                    stack.enter_context(
                        set_git_env(
                            "GIT_COMMITTER_NAME",
                            committer_name,
                            original_committer_name_env,
                        )
                    )
                if use_attribute_author:
                    stack.enter_context(
                        set_git_env(
                            "GIT_AUTHOR_NAME", committer_name, original_author_name_env
                        )
                    )

                self.repo.git.commit(cmd)
                commit_hash = self.get_head_commit_sha(short=True)
                self.io.tool_output(f"Commit {commit_hash} {commit_message}", bold=True)
                return commit_hash, commit_message

        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to commit: {err}")

    def get_rel_repo_dir(self):
        try:
            return os.path.relpath(self.repo.git_dir, os.getcwd())
        except (ValueError, OSError):
            return self.repo.git_dir

    def get_diffs(self, fnames=None):
        current_branch_has_commits = False
        try:
            active_branch = self.repo.active_branch
            try:
                commits = self.repo.iter_commits(active_branch)
                current_branch_has_commits = any(commits)
            except ANY_GIT_ERROR:
                pass
        except (TypeError,) + ANY_GIT_ERROR:
            pass

        if not fnames:
            fnames = []

        diffs = ""
        for fname in fnames:
            if not self.path_in_repo(fname):
                diffs += f"Added {fname}\n"

        try:
            if current_branch_has_commits:
                args = ["HEAD", "--"] + list(fnames)
                diffs += self.repo.git.diff(*args, stdout_as_string=False).decode(
                    self.io.encoding, "replace"
                )
                return diffs

            wd_args = ["--"] + list(fnames)
            index_args = ["--cached"] + wd_args

            diffs += self.repo.git.diff(*index_args, stdout_as_string=False).decode(
                self.io.encoding, "replace"
            )
            diffs += self.repo.git.diff(*wd_args, stdout_as_string=False).decode(
                self.io.encoding, "replace"
            )

            return diffs
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to diff: {err}")

    def diff_commits(self, pretty, from_commit, to_commit):
        args = []
        if pretty:
            args += ["--color"]
        else:
            args += ["--color=never"]

        args += [from_commit, to_commit]
        diffs = self.repo.git.diff(*args, stdout_as_string=False).decode(
            self.io.encoding, "replace"
        )

        return diffs

    def get_tracked_files(self):
        if not self.repo:
            return []

        try:
            commit = self.repo.head.commit
        except ValueError:
            commit = None
        except ANY_GIT_ERROR as err:
            self.git_repo_error = err
            self.io.tool_error(f"Unable to list files in git repo: {err}")
            self.io.tool_output("Is your git repo corrupted?")
            return []

        files = set()
        if commit:
            if commit in self.tree_files:
                files = self.tree_files[commit]
            else:
                try:
                    iterator = commit.tree.traverse()
                    blob = None
                    while True:
                        try:
                            blob = next(iterator)
                            if blob.type == "blob":
                                files.add(blob.path)
                        except IndexError:
                            self.io.tool_warning(
                                "GitRepo: Index error encountered while reading git tree object."
                                " Skipping."
                            )
                            continue
                        except StopIteration:
                            break
                except ANY_GIT_ERROR as err:
                    self.git_repo_error = err
                    self.io.tool_error(f"Unable to list files in git repo: {err}")
                    self.io.tool_output("Is your git repo corrupted?")
                    return []
                files = set(self.normalize_path(path) for path in files)
                self.tree_files[commit] = set(files)

        index = self.repo.index
        try:
            staged_files = [path for path, _ in index.entries.keys()]
            files.update(self.normalize_path(path) for path in staged_files)
        except ANY_GIT_ERROR as err:
            self.io.tool_error(f"Unable to read staged files: {err}")

        return list(files)

    def normalize_path(self, path):
        orig_path = path
        res = self.normalized_path.get(orig_path)
        if res:
            return res

        path = str(Path(PurePosixPath((Path(self.root) / path).relative_to(self.root))))
        self.normalized_path[orig_path] = path
        return path

    def is_ignored(self, path):
        if not self.repo:
            return False
        try:
            if self.repo.ignored(path):
                return True
        except ANY_GIT_ERROR:
            return False
        return False

    def path_in_repo(self, path):
        if not self.repo:
            return False
        if not path:
            return False

        tracked_files = set(self.get_tracked_files())
        return self.normalize_path(path) in tracked_files

    def get_dirty_files(self):
        dirty_files = set()

        staged_files = self.repo.git.diff("--name-only", "--cached").splitlines()
        dirty_files.update(staged_files)

        unstaged_files = self.repo.git.diff("--name-only").splitlines()
        dirty_files.update(unstaged_files)

        return list(dirty_files)

    def is_dirty(self, path=None):
        if path and not self.path_in_repo(path):
            return True

        return self.repo.is_dirty(path=path)

    def get_head_commit(self):
        try:
            return self.repo.head.commit
        except (ValueError,) + ANY_GIT_ERROR:
            return None

    def get_head_commit_sha(self, short=False):
        commit = self.get_head_commit()
        if not commit:
            return
        if short:
            return commit.hexsha[:7]
        return commit.hexsha

    def get_head_commit_message(self, default=None):
        commit = self.get_head_commit()
        if not commit:
            return default
        return commit.message

    def undo_last_commit(self, aider_commit_hashes):
        last_commit = self.get_head_commit()
        if not last_commit or not last_commit.parents:
            self.io.tool_error(
                "This is the first commit in the repository. Cannot undo."
            )
            return

        last_commit_hash = self.get_head_commit_sha(short=True)
        last_commit_message = self.get_head_commit_message("(unknown)").strip()
        last_commit_message = (last_commit_message.splitlines() or [""])[0]
        if last_commit_hash not in aider_commit_hashes:
            self.io.tool_error(
                "The last commit was not made by aider in this chat session."
            )
            self.io.tool_output(
                "You could try `/git reset --hard HEAD^` but be aware that this is a destructive"
                " command!"
            )
            return

        if len(last_commit.parents) > 1:
            self.io.tool_error(
                f"The last commit {last_commit.hexsha} has more than 1 parent, can't undo."
            )
            return

        prev_commit = last_commit.parents[0]
        changed_files_last_commit = [
            item.a_path for item in last_commit.diff(prev_commit)
        ]

        for fname in changed_files_last_commit:
            if self.repo.is_dirty(path=fname):
                self.io.tool_error(
                    f"The file {fname} has uncommitted changes. Please stash them before undoing."
                )
                return

            try:
                prev_commit.tree[fname]
            except KeyError:
                self.io.tool_error(
                    f"The file {fname} was not in the repository in the previous commit. Cannot"
                    " undo safely."
                )
                return

        local_head = self.repo.git.rev_parse("HEAD")
        current_branch = self.repo.active_branch.name
        try:
            remote_head = self.repo.git.rev_parse(f"origin/{current_branch}")
            has_origin = True
        except ANY_GIT_ERROR:
            has_origin = False

        if has_origin:
            if local_head == remote_head:
                self.io.tool_error(
                    "The last commit has already been pushed to the origin. Undoing is not"
                    " possible."
                )
                return

        restored = set()
        unrestored = set()
        for file_path in changed_files_last_commit:
            try:
                self.repo.git.checkout("HEAD~1", file_path)
                restored.add(file_path)
            except ANY_GIT_ERROR:
                unrestored.add(file_path)

        if unrestored:
            self.io.tool_error(f"Error restoring {file_path}, aborting undo.")
            self.io.tool_output("Restored files:")
            for file in restored:
                self.io.tool_output(f"  {file}")
            self.io.tool_output("Unable to restore files:")
            for file in unrestored:
                self.io.tool_output(f"  {file}")
            return

        self.repo.git.reset("--soft", "HEAD~1")

        self.io.tool_output(f"Removed: {last_commit_hash} {last_commit_message}")

        current_head_hash = self.get_head_commit_sha(short=True)
        current_head_message = self.get_head_commit_message("(unknown)").strip()
        current_head_message = (current_head_message.splitlines() or [""])[0]
        self.io.tool_output(f"Now at:  {current_head_hash} {current_head_message}")

        return True
