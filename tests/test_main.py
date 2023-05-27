import os
import tempfile
from unittest import TestCase
from unittest.mock import patch
from aider.main import main
import subprocess
from prompt_toolkit.input import create_input
from io import StringIO
from prompt_toolkit.output import DummyOutput


class TestMain(TestCase):
    def setUp(self):
        os.environ["OPENAI_API_KEY"] = "deadbeef"

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
            subprocess.run(["git", "config", "user.email", "dummy@example.com"], cwd=temp_dir)
            subprocess.run(["git", "config", "user.name", "Dummy User"], cwd=temp_dir)
            pipe_input = create_input(StringIO(""))
            main(["--yes", "foo.txt"], input=pipe_input, output=DummyOutput())
            pipe_input.close()
            self.assertTrue(os.path.exists("foo.txt"))

    def test_main_args(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            with patch("aider.main.Coder") as MockCoder:
                main(["--no-auto-commits"])
                _, kwargs = MockCoder.call_args
                assert kwargs["auto_commits"] is False

            with patch("aider.main.Coder") as MockCoder:
                main(["--auto-commits"])
                _, kwargs = MockCoder.call_args
                assert kwargs["auto_commits"] is True

            with patch("aider.main.Coder") as MockCoder:
                main([])
                _, kwargs = MockCoder.call_args
                assert kwargs["dirty_commits"] is True
                assert kwargs["auto_commits"] is True
                assert kwargs["pretty"] is True

            with patch("aider.main.Coder") as MockCoder:
                main(["--no-pretty"])
                _, kwargs = MockCoder.call_args
                assert kwargs["pretty"] is False

            with patch("aider.main.Coder") as MockCoder:
                main(["--pretty"])
                _, kwargs = MockCoder.call_args
                assert kwargs["pretty"] is True

            with patch("aider.main.Coder") as MockCoder:
                main(["--no-dirty-commits"])
                _, kwargs = MockCoder.call_args
                assert kwargs["dirty_commits"] is False

            with patch("aider.main.Coder") as MockCoder:
                main(["--dirty-commits"])
                _, kwargs = MockCoder.call_args
                assert kwargs["dirty_commits"] is True
