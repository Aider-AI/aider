import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aider.commands import Commands


class TestLoadCycles(unittest.TestCase):
    def test_load_rejects_cycles_and_continues(self):
        for indirect in (False, True):
            with self.subTest(indirect=indirect), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                first = root / "first.txt"
                second = root / "second.txt"
                target = second if indirect else root / "." / "first.txt"
                first.write_text(f"/load {target}\n/git status\n")
                second.write_text(f"/load {first}\n")
                io = MagicMock(encoding="utf-8")
                commands = Commands(io, MagicMock())
                with patch.object(commands, "cmd_git") as git:
                    commands.cmd_load(str(first))
                    git.assert_called_once_with("status")
                io.tool_error.assert_called_once()
                self.assertIn("Recursive", io.tool_error.call_args.args[0])

    def test_load_allows_repeated_non_recursive_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / "child.txt"
            child.write_text("/git status\n")
            parent = root / "parent.txt"
            parent.write_text(f"/load {child}\n/load {child}\n")
            io = MagicMock(encoding="utf-8")
            commands = Commands(io, MagicMock())
            with patch.object(commands, "cmd_git") as git:
                commands.cmd_load(str(parent))
                self.assertEqual(git.call_count, 2)
            io.tool_error.assert_not_called()

    def test_load_can_retry_after_interrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "commands.txt"
            script.write_text("/git status\n")
            io = MagicMock(encoding="utf-8")
            commands = Commands(io, MagicMock())
            with patch.object(commands, "cmd_git", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    commands.cmd_load(str(script))
            with patch.object(commands, "cmd_git") as git:
                commands.cmd_load(str(script))
                git.assert_called_once_with("status")
            io.tool_error.assert_not_called()
