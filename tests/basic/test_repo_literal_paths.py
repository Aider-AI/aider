from pathlib import Path

import git
import pytest

from aider.io import InputOutput
from aider.repo import GitRepo
from aider.utils import GitTemporaryDirectory


@pytest.mark.parametrize("target,sibling", [("[ab].txt", "a.txt"), ("file[12].txt", "file1.txt")])
@pytest.mark.parametrize("operation", ["diff", "commit"])
def test_selected_file_does_not_include_matching_sibling(target, sibling, operation):
    with GitTemporaryDirectory():
        repo = git.Repo()
        for name in (target, sibling):
            Path(name).write_text("before\n")
        repo.git.add(".")
        repo.git.commit("-m", "initial")
        for name in (target, sibling):
            Path(name).write_text("after\n")

        aider_repo = GitRepo(InputOutput(), None, ".")
        if operation == "diff":
            diff = aider_repo.get_diffs([target])
            assert f"diff --git a/{target} b/{target}" in diff
            assert f"diff --git a/{sibling} b/{sibling}" not in diff
        else:
            aider_repo.commit(fnames=[target], message="selected file only")
            assert repo.git.show("--format=", "--name-only", "HEAD") == target
            assert repo.git.diff("--", sibling)
            assert not repo.git.diff("--cached")
