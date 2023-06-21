import os
import shutil
import subprocess
import tempfile
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from prompt_toolkit.input import create_input
from prompt_toolkit.output import DummyOutput

from aider.main import main


class TestMain(TestCase):
    def setUp(self):
        os.environ["OPENAI_API_KEY"] = "deadbeef"
        self.original_cwd = os.getcwd()
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)
        self.patcher = patch("aider.coders.base_coder.check_model_availability")
        self.mock_check = self.patcher.start()
        self.mock_check.return_value = True

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tempdir)
        self.patcher.stop()

    def test_main_with_empty_dir_no_files_on_command(self):
        pipe_input = create_input(StringIO(""))
        main([], input=pipe_input, output=DummyOutput())
        pipe_input.close()

    def test_main_with_empty_dir_new_file(self):
        pipe_input = create_input(StringIO(""))
        main(["foo.txt"], input=pipe_input, output=DummyOutput())
        pipe_input.close()
        self.assertTrue(os.path.exists("foo.txt"))

    def test_main_with_empty_git_dir_new_file(self):
        subprocess.run(["git", "init"])
        subprocess.run(["git", "config", "user.email", "dummy@example.com"])
        subprocess.run(["git", "config", "user.name", "Dummy User"])
        pipe_input = create_input(StringIO(""))
        main(["--yes", "foo.txt"], input=pipe_input, output=DummyOutput())
        pipe_input.close()
        self.assertTrue(os.path.exists("foo.txt"))

    def test_main_args(self):
        with patch("aider.main.Coder.create") as MockCoder:
            main(["--no-auto-commits"])
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is False

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--auto-commits"])
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is True

        with patch("aider.main.Coder.create") as MockCoder:
            main([])
            _, kwargs = MockCoder.call_args
            assert kwargs["dirty_commits"] is True
            assert kwargs["auto_commits"] is True
            assert kwargs["pretty"] is True

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--no-pretty"])
            _, kwargs = MockCoder.call_args
            assert kwargs["pretty"] is False

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--pretty"])
            _, kwargs = MockCoder.call_args
            assert kwargs["pretty"] is True

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--no-dirty-commits"])
            _, kwargs = MockCoder.call_args
            assert kwargs["dirty_commits"] is False

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--dirty-commits"])
            _, kwargs = MockCoder.call_args
            assert kwargs["dirty_commits"] is True
