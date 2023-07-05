import os
import shutil
import subprocess
import tempfile
from unittest import TestCase
from unittest.mock import patch

from prompt_toolkit.input import DummyInput
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
        shutil.rmtree(self.tempdir, ignore_errors=True)
        self.patcher.stop()

    def test_main_with_empty_dir_no_files_on_command(self):
        main([], input=DummyInput(), output=DummyOutput())

    def test_main_with_empty_dir_new_file(self):
        main(["foo.txt"], input=DummyInput(), output=DummyOutput())
        self.assertTrue(os.path.exists("foo.txt"))

    def test_main_with_empty_git_dir_new_file(self):
        tempdir = tempfile.mkdtemp()
        os.chdir(tempdir)

        subprocess.run(["git", "init"])
        subprocess.run(["git", "config", "user.email", "dummy@example.com"])
        subprocess.run(["git", "config", "user.name", "Dummy User"])
        main(["--yes", "foo.txt"], input=DummyInput(), output=DummyOutput())
        self.assertTrue(os.path.exists("foo.txt"))

    def test_main_args(self):
        with patch("aider.main.Coder.create") as MockCoder:
            main(["--no-auto-commits"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is False

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--auto-commits"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is True

        with patch("aider.main.Coder.create") as MockCoder:
            main([], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["dirty_commits"] is True
            assert kwargs["auto_commits"] is True
            assert kwargs["pretty"] is True

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--no-pretty"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["pretty"] is False

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--pretty"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["pretty"] is True

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--no-dirty-commits"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["dirty_commits"] is False

        with patch("aider.main.Coder.create") as MockCoder:
            main(["--dirty-commits"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["dirty_commits"] is True
