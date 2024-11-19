import os
import platform
from unittest.mock import MagicMock, patch

import pytest

from aider.editor import (
    DEFAULT_EDITOR_NIX,
    DEFAULT_EDITOR_OS_X,
    DEFAULT_EDITOR_WINDOWS,
    discover_editor,
    file_editor,
    get_environment_editor,
    pipe_editor,
    print_status_message,
    write_temp_file,
)


def test_get_environment_editor():
    # Test with no environment variables set
    with patch.dict(os.environ, {}, clear=True):
        assert get_environment_editor("default") == "default"

    # Test EDITOR precedence
    with patch.dict(os.environ, {"EDITOR": "vim"}):
        assert get_environment_editor() == "vim"

    # Test VISUAL overrides EDITOR
    with patch.dict(os.environ, {"EDITOR": "vim", "VISUAL": "code"}):
        assert get_environment_editor() == "code"

    # Test AIDER_EDITOR overrides all
    with patch.dict(os.environ, {"EDITOR": "vim", "VISUAL": "code", "AIDER_EDITOR": "emacs"}):
        assert get_environment_editor() == "emacs"


def test_discover_editor():
    with patch("platform.system") as mock_system:
        # Test Windows default
        mock_system.return_value = "Windows"
        with patch.dict(os.environ, {}, clear=True):
            assert discover_editor() == [DEFAULT_EDITOR_WINDOWS]

        # Test macOS default
        mock_system.return_value = "Darwin"
        with patch.dict(os.environ, {}, clear=True):
            assert discover_editor() == [DEFAULT_EDITOR_OS_X]

        # Test Linux default
        mock_system.return_value = "Linux"
        with patch.dict(os.environ, {}, clear=True):
            assert discover_editor() == [DEFAULT_EDITOR_NIX]

    # Test editor with arguments
    with patch.dict(os.environ, {"EDITOR": 'vim -c "set noswapfile"'}):
        assert discover_editor() == ["vim", "-c", "set noswapfile"]

    # Test invalid editor command
    with patch.dict(os.environ, {"EDITOR": 'vim "unclosed quote'}):
        with pytest.raises(RuntimeError):
            discover_editor()


def test_write_temp_file():
    # Test basic file creation
    content = "test content"
    filepath = write_temp_file(content)
    assert os.path.exists(filepath)
    with open(filepath, "r") as f:
        assert f.read() == content
    os.remove(filepath)

    # Test with suffix
    filepath = write_temp_file("content", suffix="txt")
    assert filepath.endswith(".txt")
    os.remove(filepath)

    # Test with prefix
    filepath = write_temp_file("content", prefix="test_")
    assert os.path.basename(filepath).startswith("test_")
    os.remove(filepath)


def test_print_status_message(capsys):
    # Test success message
    print_status_message(True, "Success!")
    captured = capsys.readouterr()
    assert "Success!" in captured.out

    # Test failure message
    print_status_message(False, "Failed!")
    captured = capsys.readouterr()
    assert "Failed!" in captured.out


@patch("subprocess.call")
def test_file_editor(mock_call):
    # Test basic editor call
    with patch.dict(os.environ, {"EDITOR": "vim"}):
        file_editor("test.txt")
        mock_call.assert_called_once_with(["vim", "test.txt"])


def test_pipe_editor():
    test_content = "Initial content"
    modified_content = "Modified content"

    # Mock the file operations and editor call
    with (
        patch("aider.editor.write_temp_file") as mock_write,
        patch("aider.editor.file_editor") as mock_editor,
        patch("builtins.open") as mock_open,
        patch("os.remove") as mock_remove,
    ):
        # Setup mocks
        mock_write.return_value = "temp.txt"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = modified_content
        mock_open.return_value = mock_file

        # Test successful edit
        result = pipe_editor(test_content)
        assert result == modified_content
        mock_write.assert_called_once_with(test_content, None)
        mock_editor.assert_called_once_with("temp.txt")
        mock_remove.assert_called_once_with("temp.txt")

        # Test cleanup on permission error
        mock_remove.side_effect = PermissionError
        result = pipe_editor(test_content)
        assert result == modified_content
