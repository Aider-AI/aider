import os
import shutil
import tempfile
from unittest import TestCase

from aider import models
from aider.commands import Commands
from aider.io import InputOutput


class TestCommands(TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tempdir)

    def test_cmd_add_with_glob_patterns(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(models.GPT35, None, io, openai_api_key="deadbeef")
        commands = Commands(io, coder)

        # Create some test files
        with open("test1.py", "w") as f:
            f.write("print('test1')")
        with open("test2.py", "w") as f:
            f.write("print('test2')")
        with open("test.txt", "w") as f:
            f.write("test")

        # Call the cmd_add method with a glob pattern
        commands.cmd_add("*.py")

        # Check if the Python files have been added to the chat session
        self.assertIn(os.path.abspath("test1.py"), coder.abs_fnames)
        self.assertIn(os.path.abspath("test2.py"), coder.abs_fnames)

        # Check if the text file has not been added to the chat session
        self.assertNotIn(os.path.abspath("test.txt"), coder.abs_fnames)

    def test_cmd_add_no_match(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(models.GPT35, None, io, openai_api_key="deadbeef")
        commands = Commands(io, coder)

        # Call the cmd_add method with a non-existent file pattern
        commands.cmd_add("*.nonexistent")

        # Check if no files have been added to the chat session
        self.assertEqual(len(coder.abs_fnames), 0)
