import os
from unittest.mock import MagicMock, patch

from aider.editor import (
    DEFAULT_EDITOR_NIX,
    DEFAULT_EDITOR_OS_X,
    DEFAULT_EDITOR_WINDOWS,
    discover_editor,
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
    with patch.dict(os.environ, {"EDITOR": "vim"}, clear=True):
        assert get_environment_editor() == "vim"

    # Test VISUAL overrides EDITOR
    with patch.dict(os.environ, {"EDITOR": "vim", "VISUAL": "code"}):
        assert get_environment_editor() == "code"


def test_discover_editor_defaults():
    with patch("platform.system") as mock_system:
        # Test Windows default
        mock_system.return_value = "Windows"
        with patch.dict(os.environ, {}, clear=True):
            assert discover_editor() == DEFAULT_EDITOR_WINDOWS

        # Test macOS default
        mock_system.return_value = "Darwin"
        with patch.dict(os.environ, {}, clear=True):
            assert discover_editor() == DEFAULT_EDITOR_OS_X

        # Test Linux default
        mock_system.return_value = "Linux"
        with patch.dict(os.environ, {}, clear=True):
            assert discover_editor() == DEFAULT_EDITOR_NIX


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


def test_discover_editor_override():
    # Test editor override
    assert discover_editor("code") == "code"
    assert discover_editor('vim -c "set noswapfile"') == 'vim -c "set noswapfile"'


def test_pipe_editor_with_fake_editor():
    # Create a temporary Python script that logs its arguments
    import sys
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as log_f:
        log_path = log_f.name
        # Convert to raw string path to avoid escape issues on Windows
        log_path_escaped = log_path.replace("\\", "\\\\")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(f"""import sys
with open(r"{log_path_escaped}", "w") as f:
    f.write(" ".join(sys.argv))
""")
        script_path = f.name

    try:
        # Use the Python script as editor and verify it's called with .md file
        python_exe = sys.executable
        editor_cmd = f"{python_exe} {script_path}"
        pipe_editor("test content", suffix="md", editor=editor_cmd)

        # Read the log file to see what arguments were passed
        with open(log_path) as f:
            called_args = f.read().strip()

        # Verify the editor was called with a .md file
        assert called_args.endswith(".md"), f"Called args: {called_args!r}"

    finally:
        # Clean up
        os.unlink(script_path)
        os.unlink(log_path)


def test_pipe_editor():
    # Test with default editor
    test_content = "Initial content"
    modified_content = "Modified content"

    # Mock the file operations and editor call
    with (
        patch("aider.editor.write_temp_file") as mock_write,
        patch("builtins.open") as mock_open,
        patch("os.remove") as mock_remove,
        patch("subprocess.call") as mock_subprocess,
    ):
        # Setup mocks
        mock_write.return_value = "temp.txt"
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = modified_content
        mock_open.return_value = mock_file

        # Test with default editor
        result = pipe_editor(test_content)
        assert result == modified_content
        mock_write.assert_called_with(test_content, None)
        mock_subprocess.assert_called()

        # Test with custom editor
        result = pipe_editor(test_content, editor="code")
        assert result == modified_content
        mock_subprocess.assert_called()

        # Test with suffix
        result = pipe_editor(test_content, suffix="md")
        assert result == modified_content
        mock_write.assert_called_with(test_content, "md")

        # Test cleanup on permission error
        mock_remove.side_effect = PermissionError
        result = pipe_editor(test_content)
        assert result == modified_content
