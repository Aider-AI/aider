import os
import tempfile
import unittest
from unittest.mock import MagicMock
from aider.commands import Commands
from aider.io import InputOutput as IO
from aider.coder import Coder

class TestCommands(unittest.TestCase):
    def test_cmd_add(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            io = IO(pretty=False, yes=True, input_history_file=None, chat_history_file=None)
            coder = Coder(root=tmpdir)
            commands = Commands(io, coder)

            # Mock the Confirm.ask method to return True for creating files
            with unittest.mock.patch("rich.prompt.Confirm.ask", return_value=True):
                commands.cmd_add("foo.txt bar.txt")

            foo_path = os.path.join(tmpdir, "foo.txt")
            bar_path = os.path.join(tmpdir, "bar.txt")

            self.assertTrue(os.path.exists(foo_path), "foo.txt should be created")
            self.assertTrue(os.path.exists(bar_path), "bar.txt should be created")

if __name__ == "__main__":
    unittest.main()
