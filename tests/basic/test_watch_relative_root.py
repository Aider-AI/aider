from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from aider.watch import FileWatcher


@pytest.mark.parametrize("relative", [True, False])
def test_filter_root_paths(tmp_path, monkeypatch, relative):
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    source = project / "source.py"
    source.write_text("# AI! explain this\n")
    ignored = project / "ignored.py"
    ignored.write_text("# AI! explain this\n")
    gitignore = project / ".gitignore"
    gitignore.write_text("ignored.py\n")
    coder = SimpleNamespace(io=MagicMock(), root="project")
    root = "project" if relative else project
    watcher = FileWatcher(coder, root=root, gitignores=[gitignore])
    watcher.get_ai_comments = MagicMock(return_value=([1], ["AI!"], "!"))
    assert watcher.filter_func(None, str(source))
    assert not watcher.filter_func(None, str(ignored))
    assert not watcher.filter_func(None, str(tmp_path / "outside.py"))
    watcher.get_ai_comments.assert_called_once_with(str(source))
