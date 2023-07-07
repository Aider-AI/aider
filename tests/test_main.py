import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput

from aider.dump import dump  # noqa: F401
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
        main(["--no-git"], input=DummyInput(), output=DummyOutput())

    def test_main_with_empty_dir_new_file(self):
        main(["foo.txt", "--yes"], input=DummyInput(), output=DummyOutput())
        self.assertTrue(os.path.exists("foo.txt"))

    def test_main_with_empty_git_dir_new_file(self):
        subprocess.run(["git", "init"])
        subprocess.run(["git", "config", "user.email", "dummy@example.com"])
        subprocess.run(["git", "config", "user.name", "Dummy User"])
        main(["--yes", "foo.txt"], input=DummyInput(), output=DummyOutput())
        self.assertTrue(os.path.exists("foo.txt"))

    def test_main_with_git_config_yml(self):
        subprocess.run(["git", "init"])
        subprocess.run(["git", "config", "user.email", "dummy@example.com"])
        subprocess.run(["git", "config", "user.name", "Dummy User"])

        Path(".aider.conf.yml").write_text("no-auto-commits: true\n")
        with patch("aider.main.Coder.create") as MockCoder:
            main([], input=DummyInput(), output=DummyOutput())
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is False

        Path(".aider.conf.yml").write_text("auto-commits: true\n")
        with patch("aider.main.Coder.create") as MockCoder:
            main([], input=DummyInput(), output=DummyOutput())
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is True

    def test_main_with_empty_git_dir_new_subdir_file(self):
        subprocess.run(["git", "init"])
        subprocess.run(["git", "config", "user.email", "dummy@example.com"])
        subprocess.run(["git", "config", "user.name", "Dummy User"])
        subdir = Path("subdir")
        subdir.mkdir()
        fname = subdir / "foo.txt"
        fname.touch()
        subprocess.run(["git", "add", str(subdir)])
        subprocess.run(["git", "commit", "-m", "added"])

        # This will throw a git error on windows if get_tracked_files doesn't
        # properly convert git/posix/paths to git\posix\paths.
        # Because aider will try and `git add` a file that's already in the repo.
        main(["--yes", str(fname)], input=DummyInput(), output=DummyOutput())

    def test_main_args(self):
        with patch("aider.main.Coder.create") as MockCoder:
            # --yes will just ok the git repo without blocking on input
            # following calls to main will see the new repo already
            main(["--no-auto-commits", "--yes"], input=DummyInput())
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
