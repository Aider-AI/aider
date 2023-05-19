import os
import tempfile
from unittest import TestCase
from aider.io import InputOutput
from aider.coder import Coder
from aider.commands import Commands

class TestCommands(TestCase):
    def test_cmd_add(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            io = InputOutput(pretty=True, yes=True)
            coder = Coder(io)
            commands = Commands(io, coder)

            commands.cmd_add(['foo.txt', 'bar.txt'])

            self.assertTrue(os.path.exists('foo.txt'))
            self.assertTrue(os.path.exists('bar.txt'))

            os.chdir(original_cwd)
