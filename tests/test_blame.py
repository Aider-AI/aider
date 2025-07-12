import os
from unittest.mock import MagicMock, patch
import git
from io import StringIO

from aider.commands import Commands
from aider.io import InputOutput
from aider.repo import GitRepo


def test_cmd_blame(monkeypatch, tmp_path):
    # Create a git repo
    os.chdir(tmp_path)
    io = InputOutput(pretty=False, yes=True)

    # Initialize a real GitRepo, after initializing the repo
    repo_path = str(tmp_path)
    GitRepo.repo = git.Repo.init(repo_path)

    repo = GitRepo(io, fnames=[], git_dname=repo_path)

    # Mock the coder and its attributes
    coder = MagicMock()
    coder.io = io
    coder.repo = repo

    # Initialize Commands with the mocked coder
    commands = Commands(io, coder)

    # Create a file and commit it
    file_path = tmp_path / "test_file.py"
    file_path.write_text("line 1\nline 2\nline 3\n")
    repo.repo.git.add("test_file.py")
    repo.repo.git.commit("-m", "initial commit")

    # Modify the file and commit again
    file_path.write_text("line 1\nnew line 2\nline 3\n")
    repo.repo.git.add("test_file.py")
    repo.repo.git.commit("-m", "second commit")

    # Mock io.tool_output to capture the output
    captured_output = []
    io.tool_output = lambda *args, **kwargs: captured_output.append(str(args[0]))

    # Run the blame command
    commands.cmd_blame("test_file.py:2")

    # Check the output
    assert len(captured_output) > 0, "No output was captured"
    output = "".join(captured_output)
    assert "second commit" in output
    assert "new line 2" in output

    # Test blame on a line from the first commit
    captured_output.clear()
    commands.cmd_blame("test_file.py:1")
    output = "".join(captured_output)
    assert "initial commit" in output
    assert "line 1" in output

    # Test invalid format
    captured_output.clear()
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        commands.cmd_blame("test_file.py")
        output = mock_stdout.getvalue()
    assert "Invalid format" in output

    # Test file not found
    captured_output.clear()
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        commands.cmd_blame("non_existent_file.py:1")
        output = mock_stdout.getvalue()
    assert "not in the git repository" in output

    # Test line number out of bounds
    captured_output.clear()
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        commands.cmd_blame("test_file.py:100")
        output = mock_stdout.getvalue()
    assert "has only 3 lines" in output
