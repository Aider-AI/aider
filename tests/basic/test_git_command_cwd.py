from types import SimpleNamespace
from unittest.mock import MagicMock

import git
import pytest

from aider.commands import Commands


@pytest.mark.parametrize("launch_directory", ["nested", "other_repo"])
def test_git_command_uses_coder_repository(tmp_path, monkeypatch, launch_directory):
    target = tmp_path / "target"
    target.mkdir()
    target_repo = git.Repo.init(target)
    (target / "change.txt").write_text("target change\n", encoding="utf-8")

    if launch_directory == "nested":
        launch_path = target / "nested"
        launch_path.mkdir()
        other_repo = None
    else:
        launch_path = tmp_path / "other"
        launch_path.mkdir()
        other_repo = git.Repo.init(launch_path)
        (launch_path / "change.txt").write_text("other change\n", encoding="utf-8")
    monkeypatch.chdir(launch_path)
    io = MagicMock()
    io.encoding = "utf-8"
    commands = Commands(io, SimpleNamespace(root=str(target)))

    commands.cmd_git("add change.txt")

    assert target_repo.git.diff("--cached", "--name-only") == "change.txt"
    if other_repo is not None:
        assert other_repo.git.diff("--cached", "--name-only") == ""
