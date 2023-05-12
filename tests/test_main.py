import os
import sys
import tempfile
from unittest import TestCase
from aider.main import main
import subprocess


class TestMain(TestCase):
    def test_main_with_empty_dir_no_files_on_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            with open(os.devnull, "r") as dev_null:
                save_stdin = sys.stdin
                sys.stdin = dev_null
                main()
                sys.stdin = save_stdin

    def test_main_with_empty_dir_new_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            with open(os.devnull, "r") as dev_null:
                save_stdin = sys.stdin
                sys.stdin = dev_null
                main(["foo.txt"])
                sys.stdin = save_stdin
                self.assertTrue(os.path.exists("foo.txt"))

    def test_main_with_empty_git_dir_new_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            subprocess.run(["git", "init"])
            with open(os.devnull, "r") as dev_null:
                save_stdin = sys.stdin
                sys.stdin = dev_null
                main(["--yes", "foo.txt"])
                sys.stdin = save_stdin
