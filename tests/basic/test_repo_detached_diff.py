from pathlib import Path

import git
import pytest

from aider.io import InputOutput
from aider.repo import GitRepo
from aider.utils import GitTemporaryDirectory


@pytest.mark.parametrize("detached", [False, True])
@pytest.mark.parametrize("working", ["original\n", "final\n"])
@pytest.mark.parametrize("fnames", [None, ["example.txt"]])
def test_diffs_compare_final_content_to_head(detached, working, fnames):
    with GitTemporaryDirectory():
        repo = git.Repo()
        path = Path("example.txt")
        path.write_text("original\n")
        repo.git.add(str(path))
        repo.git.commit("-m", "initial")
        if detached:
            repo.git.checkout("--detach", "HEAD")

        path.write_text("intermediate\n")
        repo.git.add(str(path))
        path.write_text(working)

        actual = GitRepo(InputOutput(), None, ".").get_diffs(fnames)
        expected = repo.git.diff("HEAD", "--", "example.txt", stdout_as_string=False)
        assert actual == expected.decode("utf-8")
        assert "intermediate" not in actual
