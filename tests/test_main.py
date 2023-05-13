import os
import tempfile
from unittest import TestCase
from aider.main import main
import subprocess
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput


class TestMain(TestCase):
    def test_main_with_empty_dir_no_files_on_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            pipe_input = create_pipe_input()
            save_stdin = sys.stdin
            sys.stdin = pipe_input
            main([], input=pipe_input, output=DummyOutput())
            sys.stdin = save_stdin
            pipe_input.close()

    def test_main_with_empty_dir_new_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            pipe_input = create_pipe_input()
            save_stdin = sys.stdin
            sys.stdin = pipe_input
            main(["foo.txt"], input=pipe_input, output=DummyOutput())
            sys.stdin = save_stdin
            pipe_input.close()
            self.assertTrue(os.path.exists("foo.txt"))

    def test_main_with_empty_git_dir_new_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            subprocess.run(["git", "init"], cwd=temp_dir)
            pipe_input = create_pipe_input()
            save_stdin = sys.stdin
            sys.stdin = pipe_input
            main(["--yes", "foo.txt"], input=pipe_input, output=DummyOutput())
            sys.stdin = save_stdin
            pipe_input.close()
            self.assertTrue(os.path.exists("foo.txt"))
