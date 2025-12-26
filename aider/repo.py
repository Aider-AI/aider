import os
import time
from pathlib import Path

import pathspec

from aider import utils
from aider.vcs.git import GitVCS
from aider.vcs.jj import JjVCS

VCS_CLASSES = [GitVCS, JjVCS]


class Repo:
    vcs = None
    aider_ignore_file = None
    aider_ignore_spec = None
    aider_ignore_ts = 0
    aider_ignore_last_check = 0
    subtree_only = False
    ignore_file_cache = {}

    def __init__(
        self,
        io,
        fnames,
        git_dname,
        aider_ignore_file=None,
        models=None,
        attribute_author=True,
        attribute_committer=True,
        attribute_commit_message_author=False,
        attribute_commit_message_committer=False,
        commit_prompt=None,
        subtree_only=False,
        git_commit_verify=True,
        attribute_co_authored_by=False,
        vcs="auto",
    ):
        self.io = io
        self.subtree_only = subtree_only
        self.ignore_file_cache = {}

        if vcs == "git":
            vcs_classes = [GitVCS]
        elif vcs == "jj":
            vcs_classes = [JjVCS]
        elif vcs == "auto":
            vcs_classes = VCS_CLASSES
        else:
            vcs_classes = []

        for vcs_class in vcs_classes:
            try:
                self.vcs = vcs_class(
                    io,
                    fnames=fnames,
                    git_dname=git_dname,
                    models=models,
                    attribute_author=attribute_author,
                    attribute_committer=attribute_committer,
                    attribute_commit_message_author=attribute_commit_message_author,
                    attribute_commit_message_committer=attribute_commit_message_committer,
                    commit_prompt=commit_prompt,
                    git_commit_verify=git_commit_verify,
                    attribute_co_authored_by=attribute_co_authored_by,
                )
                break
            except (FileNotFoundError, NotImplementedError):
                continue

        if not self.vcs:
            raise FileNotFoundError

        self.root = self.vcs.root

        if aider_ignore_file:
            self.aider_ignore_file = Path(aider_ignore_file)

    def __getattr__(self, name):
        if self.vcs and hasattr(self.vcs, name):
            return getattr(self.vcs, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def get_tracked_files(self):
        if not self.vcs:
            return []

        res = [fname for fname in self.vcs.get_tracked_files() if not self.ignored_file(fname)]

        return res

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

    def vcs_ignored_file(self, path):
        return self.vcs.is_ignored(path)

    def ignored_file(self, fname):
        self.refresh_aider_ignore()

        if fname in self.ignore_file_cache:
            return self.ignore_file_cache[fname]

        result = self.ignored_file_raw(fname)
        self.ignore_file_cache[fname] = result
        return result

    def ignored_file_raw(self, fname):
        if self.vcs and self.vcs.is_ignored(fname):
            return True

        if self.subtree_only:
            try:
                fname_path = Path(self.normalize_path(fname))
                cwd_path = Path.cwd().resolve().relative_to(Path(self.root).resolve())
            except ValueError:
                return True

            if cwd_path not in fname_path.parents and fname_path != cwd_path:
                return True

        if not self.aider_ignore_file or not self.aider_ignore_file.is_file():
            return False

        try:
            fname = self.normalize_path(fname)
        except ValueError:
            return True

        return self.aider_ignore_spec.match_file(fname)

    def abs_root_path(self, path):
        res = Path(self.root) / path
        return utils.safe_abs_path(res)
