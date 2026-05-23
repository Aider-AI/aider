import os
import time
import pathspec
from pathlib import Path, PurePosixPath
from aider import utils

class DirectoryRepo:
    """
        A substitute for GitRepo; lets Aider run mostly full-featured without a git repo 
        (for instance, with another version-control tool like fossil).
    """
    aider_ignore_file = None
    aider_ignore_spec = None
    aider_ignore_ts = 0
    aider_ignore_last_check = 0

    def __init__(
        self,
        git_dname,
        aider_ignore_file=None,
    ):
        self.normalized_path_cache = {}
        self.ignore_file_cache = {}
        self.root = utils.safe_abs_path(Path(git_dname or ".").resolve())
        if aider_ignore_file:
            self.aider_ignore_file = Path(aider_ignore_file)

    def commit(self, fnames=None, context=None, message=None, aider_edits=False):
        return

    def get_rel_repo_dir(self):
        return "non-git directory"

    def get_tracked_files(self):
        files = []
        for dirpath, _, filenames in os.walk(self.root):
            for filename in filenames:
                file_path = self.normalize_path(os.path.join(dirpath, filename))
                if self.ignored_file(file_path):
                    continue
                files.append(file_path)
        return files

    def normalize_path(self, path):
        orig_path = path
        res = self.normalized_path_cache.get(orig_path)
        if res:
            return res

        path = str(Path(PurePosixPath((Path(self.root) / path).relative_to(self.root))))
        self.normalized_path_cache[orig_path] = path
        return path

    def refresh_aider_ignore(self):
        if not self.aider_ignore_file:
            return

        current_time = time.time()
        if current_time - self.aider_ignore_last_check < 1:
            return

        self.aider_ignore_last_check = current_time

        if not self.aider_ignore_file.is_file():
            return

        mtime = self.aider_ignore_file.stat().st_mtime
        if mtime != self.aider_ignore_ts:
            self.aider_ignore_ts = mtime
            self.ignore_file_cache = {}
            lines = self.aider_ignore_file.read_text().splitlines()
            self.aider_ignore_spec = pathspec.PathSpec.from_lines(
                pathspec.patterns.GitWildMatchPattern,
                lines,
            )

    def git_ignored_file(self, path):
        return False

    def ignored_file(self, fname):
        self.refresh_aider_ignore()

        if fname in self.ignore_file_cache:
            return self.ignore_file_cache[fname]

        is_ignored = self.ignored_file_raw(fname)
        self.ignore_file_cache[fname] = is_ignored
        return is_ignored

    def ignored_file_raw(self, fname):
        try:
            fname = self.normalize_path(fname)
        except ValueError:
            return True

        if '.aider' in str(fname):
            return True

        if not self.aider_ignore_file or not self.aider_ignore_file.is_file():
            return False

        return self.aider_ignore_spec.match_file(fname)

    def path_in_repo(self, path):
        if not path:
            return

        tracked_files = set(self.get_tracked_files())
        return self.normalize_path(path) in tracked_files

    def get_dirty_files(self):
        return []

    def is_dirty(self, path=None):
        return False
