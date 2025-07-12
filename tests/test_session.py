import os
import json
from pathlib import Path
from unittest.mock import MagicMock

import git

from aider.commands import Commands
from aider.io import InputOutput
from aider.repo import GitRepo


def test_session_save_and_load(monkeypatch, tmp_path):
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
    # Make coder.root available for session path resolution
    coder.root = git_repo.root
    
    def get_rel_fname(path):
        return os.path.relpath(path, git_repo.root)

    coder.get_rel_fname.side_effect = get_rel_fname


    # Set up initial state on the coder
    coder.abs_fnames = {str(file1_path.resolve())}
    coder.abs_read_only_fnames = {str(file2_path.resolve())}
    coder.done_messages = [{"role": "user", "content": "hello"}]
    coder.cur_messages = [] # Explicitly clear this for the test

    # Mock original_read_only_fnames for reset behavior
    commands = Commands(io, coder, original_read_only_fnames=coder.abs_read_only_fnames)

    # --- Test /session_save ---
    session_name = "my_test_session"
    commands.cmd_session_save(session_name)

    sessions_dir = Path(git_repo.root) / ".aider" / "sessions"
    session_file = sessions_dir / f"{session_name}.json"

    assert session_file.exists()

    with open(session_file, "r") as f:
        data = json.load(f)

    assert data["chat_history"] == coder.done_messages
    assert set(data["editable_files"]) == coder.abs_fnames
    assert set(data["read_only_files"]) == coder.abs_read_only_fnames
    assert "version" in data
    assert "timestamp" in data

    # --- Test /session_load ---

    # First, reset the coder's state to simulate a new session
    commands.cmd_reset("")
    assert not coder.abs_fnames
    # After reset, original read-only files should remain
    assert coder.abs_read_only_fnames == {str(file2_path.resolve())}
    assert not coder.done_messages

    # Now, load the session
    commands.cmd_session_load(session_name)

    # Verify the state is restored
    assert coder.done_messages == data["chat_history"]
    assert coder.abs_fnames == set(data["editable_files"])
    assert coder.abs_read_only_fnames == set(data["read_only_files"])

    # --- Test loading a non-existent session ---
    captured_errors = []
    io.tool_error = lambda msg: captured_errors.append(msg)
    commands.cmd_session_load("non_existent_session")
    assert "Session 'non_existent_session' not found." in captured_errors
