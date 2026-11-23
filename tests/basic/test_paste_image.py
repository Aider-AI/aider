from unittest.mock import MagicMock

import pytest
from PIL import Image

from aider.commands import Commands


@pytest.mark.parametrize("name", ["capture.jpg", "capture.jpeg", "capture.png"])
def test_paste_rgba_image(tmp_path, monkeypatch, name):
    clipboard = Image.new("RGBA", (3, 2), (80, 120, 160, 128))
    monkeypatch.setattr("aider.commands.ImageGrab.grabclipboard", lambda: clipboard)
    monkeypatch.setattr("aider.commands.tempfile.mkdtemp", lambda: str(tmp_path))
    io = MagicMock()
    coder = MagicMock()
    coder.abs_fnames = set()

    Commands(io, coder).cmd_paste(name)

    io.tool_error.assert_not_called()
    assert coder.abs_fnames == {str((tmp_path / name).resolve())}
    coder.check_added_files.assert_called_once()
    with Image.open(tmp_path / name) as saved:
        assert saved.size == clipboard.size
        if name.endswith(".png"):
            assert saved.mode == "RGBA"
            assert saved.getpixel((0, 0)) == (80, 120, 160, 128)
        else:
            assert saved.format == "JPEG"
            assert saved.mode == "RGB"
    assert clipboard.mode == "RGBA"
