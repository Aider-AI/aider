import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import git

from aider.commands import Commands
from aider.io import InputOutput
from aider.repo import GitRepo


def test_session_management(monkeypatch, tmp_path):
    # Setup: Create a git repo and a file
    os.chdir(tmp_path)
    io = InputOutput(pretty=False, yes=True)
    repo_path = str(tmp_path)
    repo = git.Repo.init(repo_path)

    # Use a real GitRepo
    git_repo = GitRepo(io, fnames=[], git_dname=repo_path)

    # Create some files
    file1_path = tmp_path / "file1.py"
    file1_path.write_text("print('hello')\n")
    file2_path = tmp_path / "file2.py"
    file2_path.write_text("print('world')\n")
    repo.git.add(".")
    repo.git.commit("-m", "initial commit")

    # Mock the coder
    coder = MagicMock()
    coder.io = io
    coder.repo = git_repo
    coder.root = git_repo.root

    def get_rel_fname(path):
        return os.path.relpath(path, git_repo.root)

    coder.get_rel_fname.side_effect = get_rel_fname

    # Set up initial state on the coder
    coder.abs_fnames = {str(file1_path.resolve())}
    coder.abs_read_only_fnames = {str(file2_path.resolve())}
    coder.done_messages = [{"role": "user", "content": "hello"}]
    coder.cur_messages = []

    commands = Commands(io, coder, original_read_only_fnames=coder.abs_read_only_fnames)

    # --- Test /session save ---
    session_name = "my_test_session"
    commands.cmd_session(f"save {session_name}")

    sessions_dir = Path(git_repo.root) / ".aider" / "sessions"
    session_file = sessions_dir / f"{session_name}.json"
    assert session_file.exists()

    with open(session_file, "r") as f:
        data = json.load(f)
    assert data["chat_history"] == coder.done_messages

    # --- Test /session list ---
    captured_output = []
    io.tool_output = lambda msg: captured_output.append(msg)
    commands.cmd_session("list")
    assert f"- {session_name}" in captured_output

    # --- Test /session view ---
    captured_output.clear()
    commands.cmd_session(f"view {session_name}")
    output = "".join(captured_output)
    assert session_name in output
    assert "file1.py" in output
    assert "file2.py" in output
    assert "hello" in output  # from chat history

    # --- Test /session load ---
    commands.cmd_reset("")  # Reset state
    commands.cmd_session(f"load {session_name}")
    assert coder.done_messages == data["chat_history"]
    assert coder.abs_fnames == set(data["editable_files"])

    # --- Test /session delete ---
    commands.cmd_session(f"delete {session_name}")
    assert not session_file.exists()

    # --- Test invalid command ---
    captured_errors = []
    io.tool_error = lambda msg: captured_errors.append(msg)
    commands.cmd_session("invalid_subcommand")
    assert "Invalid subcommand" in captured_errors[0]
