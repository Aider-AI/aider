import os
import tempfile
import unittest
from unittest import TestCase
from aider.main import main
import subprocess
from prompt_toolkit.input import create_input
from io import StringIO
from prompt_toolkit.output import DummyOutput


class TestMain(TestCase):
    def test_main_with_empty_dir_no_files_on_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            pipe_input = create_input(StringIO(""))
            main([], input=pipe_input, output=DummyOutput())
            pipe_input.close()

    def test_main_with_empty_dir_new_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            pipe_input = create_input(StringIO(""))
            main(["foo.txt"], input=pipe_input, output=DummyOutput())
            pipe_input.close()
            self.assertTrue(os.path.exists("foo.txt"))

    def test_main_with_empty_git_dir_new_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            subprocess.run(["git", "init"], cwd=temp_dir)
            pipe_input = create_input(StringIO(""))
            main(["--yes", "foo.txt"], input=pipe_input, output=DummyOutput())
            pipe_input.close()
            self.assertTrue(os.path.exists("foo.txt"))

    def test_main_no_auto_commits(self):
        with unittest.mock.patch("aider.main.Coder") as MockCoder:
            with tempfile.TemporaryDirectory() as temp_dir:
                os.chdir(temp_dir)
                subprocess.run(["git", "init"], cwd=temp_dir)
                pipe_input = create_input(StringIO(""))
                main(["--no-auto-commits"], input=pipe_input, output=DummyOutput())
                pipe_input.close()

            mock_coder_instance = MockCoder.return_value
            self.assertFalse(mock_coder_instance.auto_commits)
