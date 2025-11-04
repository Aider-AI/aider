import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest import TestCase, mock

from aider.coders import Coder
from aider.commands import Commands
from aider.io import InputOutput
from aider.models import Model
from aider.utils import GitTemporaryDirectory


class TestSessionCommands(TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

        self.GPT35 = Model("gpt-3.5-turbo")

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    async def test_cmd_save_session_basic(self):
        """Test basic session save functionality"""
        with GitTemporaryDirectory() as repo_dir:
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = await Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create test files
            test_files = {
                "file1.txt": "Content of file 1",
                "file2.py": "print('Content of file 2')",
                "subdir/file3.md": "# Content of file 3",
            }

            for file_path, content in test_files.items():
                full_path = Path(repo_dir) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)

            # Add files to chat
            commands.cmd_add("file1.txt file2.py")
            commands.cmd_read_only("subdir/file3.md")

            # Add chat history
            coder.done_messages = [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
            coder.cur_messages = [
                {"role": "user", "content": "Can you help me?"},
            ]

            # Save session
            session_name = "test_session"
            commands.cmd_save_session(session_name)

            # Verify session file was created
            session_file = Path(".aider") / "sessions" / f"{session_name}.json"
            self.assertTrue(session_file.exists())

            # Verify session content
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            self.assertEqual(session_data["version"], "1.0")
            self.assertEqual(session_data["session_name"], session_name)
            self.assertEqual(session_data["model"], self.GPT35.name)
            self.assertEqual(session_data["edit_format"], coder.edit_format)

            # Verify chat history
            chat_history = session_data["chat_history"]
            self.assertEqual(chat_history["done_messages"], coder.done_messages)
            self.assertEqual(chat_history["cur_messages"], coder.cur_messages)

            # Verify files
            files = session_data["files"]
            self.assertEqual(set(files["editable"]), {"file1.txt", "file2.py"})
            self.assertEqual(set(files["read_only"]), {"subdir/file3.md"})
            self.assertEqual(files["read_only_stubs"], [])

            # Verify settings
            settings = session_data["settings"]
            self.assertEqual(settings["root"], coder.root)
            self.assertEqual(settings["auto_commits"], coder.auto_commits)
            self.assertEqual(settings["auto_lint"], coder.auto_lint)
            self.assertEqual(settings["auto_test"], coder.auto_test)

    async def test_cmd_load_session_basic(self):
        """Test basic session load functionality"""
        with GitTemporaryDirectory() as repo_dir:
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = await Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create test files
            test_files = {
                "file1.txt": "Content of file 1",
                "file2.py": "print('Content of file 2')",
                "subdir/file3.md": "# Content of file 3",
            }

            for file_path, content in test_files.items():
                full_path = Path(repo_dir) / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)

            # Create a session file manually
            session_data = {
                "version": "1.0",
                "timestamp": time.time(),
                "session_name": "test_session",
                "model": self.GPT35.name,
                "edit_format": "diff",
                "chat_history": {
                    "done_messages": [
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi there!"},
                    ],
                    "cur_messages": [
                        {"role": "user", "content": "Can you help me?"},
                    ],
                },
                "files": {
                    "editable": ["file1.txt", "file2.py"],
                    "read_only": ["subdir/file3.md"],
                    "read_only_stubs": [],
                },
                "settings": {
                    "root": str(repo_dir),
                    "auto_commits": True,
                    "auto_lint": False,
                    "auto_test": False,
                },
            }

            # Save session file
            session_file = Path(".aider") / "sessions" / "test_session.json"
            session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            # Load the session
            commands.cmd_load_session("test_session")

            # Verify chat history was loaded
            self.assertEqual(coder.done_messages, session_data["chat_history"]["done_messages"])
            self.assertEqual(coder.cur_messages, session_data["chat_history"]["cur_messages"])

            # Verify files were loaded
            editable_files = {coder.get_rel_fname(f) for f in coder.abs_fnames}
            read_only_files = {coder.get_rel_fname(f) for f in coder.abs_read_only_fnames}

            self.assertEqual(editable_files, {"file1.txt", "file2.py"})
            self.assertEqual(read_only_files, {"subdir/file3.md"})
            self.assertEqual(len(coder.abs_read_only_stubs_fnames), 0)

            # Verify settings were loaded
            self.assertEqual(coder.auto_commits, True)
            self.assertEqual(coder.auto_lint, False)
            self.assertEqual(coder.auto_test, False)

    async def test_cmd_list_sessions_basic(self):
        """Test basic session list functionality"""
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = await Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create multiple session files
            sessions_data = [
                {
                    "version": "1.0",
                    "timestamp": time.time() - 3600,  # 1 hour ago
                    "session_name": "session1",
                    "model": "gpt-3.5-turbo",
                    "edit_format": "diff",
                    "chat_history": {"done_messages": [], "cur_messages": []},
                    "files": {"editable": [], "read_only": [], "read_only_stubs": []},
                    "settings": {
                        "root": ".",
                        "auto_commits": True,
                        "auto_lint": False,
                        "auto_test": False,
                    },
                },
                {
                    "version": "1.0",
                    "timestamp": time.time(),  # current time
                    "session_name": "session2",
                    "model": "gpt-4",
                    "edit_format": "whole",
                    "chat_history": {"done_messages": [], "cur_messages": []},
                    "files": {"editable": [], "read_only": [], "read_only_stubs": []},
                    "settings": {
                        "root": ".",
                        "auto_commits": True,
                        "auto_lint": False,
                        "auto_test": False,
                    },
                },
            ]

            # Save session files
            session_dir = Path(".aider") / "sessions"
            session_dir.mkdir(parents=True, exist_ok=True)

            for session_data in sessions_data:
                session_file = session_dir / f"{session_data['session_name']}.json"
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)

            # Capture output of list_sessions
            with mock.patch.object(io, "tool_output") as mock_tool_output:
                commands.cmd_list_sessions("")

                # Verify that tool_output was called with session information
                calls = mock_tool_output.call_args_list

                # Check that we got at least the header and session entries
                self.assertGreater(len(calls), 2)

                # Check that both sessions are listed
                output_text = "\n".join([call[0][0] if call[0] else "" for call in calls])
                self.assertIn("session1", output_text)
                self.assertIn("session2", output_text)
                self.assertIn("gpt-3.5-turbo", output_text)
                self.assertIn("gpt-4", output_text)
