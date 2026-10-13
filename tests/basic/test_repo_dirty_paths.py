from pathlib import Path
from unittest.mock import MagicMock

import git

from aider.repo import GitRepo
from aider.utils import GitTemporaryDirectory


def test_dirty_files_preserve_unicode_paths():
    with GitTemporaryDirectory():
        repo = git.Repo()
        repo.git.config("core.quotePath", "true")
        filenames = ["café.py", "你好.py"]
        for filename in filenames:
            Path(filename).write_text("before\n", encoding="utf-8")
        repo.git.add(*filenames)
        repo.git.commit("-m", "initial")
        for filename in filenames:
            Path(filename).write_text("after\n", encoding="utf-8")
        repo.git.add(filenames[0])

        git_repo = GitRepo(MagicMock(), None, ".")

        assert set(git_repo.get_dirty_files()) == set(filenames)


def test_clean_repo_has_no_dirty_paths():
    with GitTemporaryDirectory():
        git_repo = GitRepo(MagicMock(), None, ".")

        assert git_repo.get_dirty_files() == []
