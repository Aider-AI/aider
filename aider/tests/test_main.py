import os
import subprocess
import tempfile
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

import git
from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput

from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.main import check_gitignore, main, setup_git
from aider.utils import GitTemporaryDirectory, IgnorantTemporaryDirectory, make_repo


class TestMain(TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["OPENAI_API_KEY"] = "deadbeef"
        self.original_cwd = os.getcwd()
        self.tempdir_obj = IgnorantTemporaryDirectory()
        self.tempdir = self.tempdir_obj.name
        os.chdir(self.tempdir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tempdir_obj.cleanup()
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_main_with_empty_dir_no_files_on_command(self):
        main(["--no-git"], input=DummyInput(), output=DummyOutput())

    def test_main_with_emptqy_dir_new_file(self):
        main(["foo.txt", "--yes", "--no-git"], input=DummyInput(), output=DummyOutput())
        self.assertTrue(os.path.exists("foo.txt"))

    @patch("aider.repo.GitRepo.get_commit_message", return_value="mock commit message")
    def test_main_with_empty_git_dir_new_file(self, _):
        make_repo()
        main(["--yes", "foo.txt"], input=DummyInput(), output=DummyOutput())
        self.assertTrue(os.path.exists("foo.txt"))

    @patch("aider.repo.GitRepo.get_commit_message", return_value="mock commit message")
    def test_main_with_empty_git_dir_new_files(self, _):
        make_repo()
        main(["--yes", "foo.txt", "bar.txt"], input=DummyInput(), output=DummyOutput())
        self.assertTrue(os.path.exists("foo.txt"))
        self.assertTrue(os.path.exists("bar.txt"))

    def test_main_with_dname_and_fname(self):
        subdir = Path("subdir")
        subdir.mkdir()
        make_repo(str(subdir))
        res = main(["subdir", "foo.txt"], input=DummyInput(), output=DummyOutput())
        self.assertNotEqual(res, None)

    @patch("aider.repo.GitRepo.get_commit_message", return_value="mock commit message")
    def test_main_with_subdir_repo_fnames(self, _):
        subdir = Path("subdir")
        subdir.mkdir()
        make_repo(str(subdir))
        main(
            ["--yes", str(subdir / "foo.txt"), str(subdir / "bar.txt")],
            input=DummyInput(),
            output=DummyOutput(),
        )
        self.assertTrue((subdir / "foo.txt").exists())
        self.assertTrue((subdir / "bar.txt").exists())

    def test_main_with_git_config_yml(self):
        make_repo()

        Path(".aider.conf.yml").write_text("auto-commits: false\n")
        with patch("aider.main.Coder.create") as MockCoder:
            main(["--yes"], input=DummyInput(), output=DummyOutput())
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is False

        Path(".aider.conf.yml").write_text("auto-commits: true\n")
        with patch("aider.main.Coder.create") as MockCoder:
            main([], input=DummyInput(), output=DummyOutput())
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is True

    def test_main_with_empty_git_dir_new_subdir_file(self):
        make_repo()
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

    def test_setup_git(self):
        io = InputOutput(pretty=False, yes=True)
        git_root = setup_git(None, io)
        git_root = Path(git_root).resolve()
        self.assertEqual(git_root, Path(self.tempdir).resolve())

        self.assertTrue(git.Repo(self.tempdir))

        gitignore = Path.cwd() / ".gitignore"
        self.assertTrue(gitignore.exists())
        self.assertEqual(".aider*", gitignore.read_text().splitlines()[0])

    def test_check_gitignore(self):
        with GitTemporaryDirectory():
            os.environ["GIT_CONFIG_GLOBAL"] = "globalgitconfig"

            io = InputOutput(pretty=False, yes=True)
            cwd = Path.cwd()
            gitignore = cwd / ".gitignore"

            self.assertFalse(gitignore.exists())
            check_gitignore(cwd, io)
            self.assertTrue(gitignore.exists())

            self.assertEqual(".aider*", gitignore.read_text().splitlines()[0])

            gitignore.write_text("one\ntwo\n")
            check_gitignore(cwd, io)
            self.assertEqual("one\ntwo\n.aider*\n", gitignore.read_text())
            del os.environ["GIT_CONFIG_GLOBAL"]

    def test_main_git_ignore(self):
        cwd = Path().cwd()
        self.assertFalse((cwd / ".git").exists())
        self.assertFalse((cwd / ".gitignore").exists())

        with patch("aider.main.Coder.create"):
            main(["--yes"], input=DummyInput())

        self.assertTrue((cwd / ".git").exists())
        self.assertTrue((cwd / ".gitignore").exists())

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

    def test_message_file_flag(self):
        message_file_content = "This is a test message from a file."
        message_file_path = tempfile.mktemp()
        with open(message_file_path, "w", encoding="utf-8") as message_file:
            message_file.write(message_file_content)

        with patch("aider.main.Coder.create") as MockCoder:
            MockCoder.return_value.run = MagicMock()
            main(
                ["--yes", "--message-file", message_file_path],
                input=DummyInput(),
                output=DummyOutput(),
            )
            MockCoder.return_value.run.assert_called_once_with(with_message=message_file_content)

        os.remove(message_file_path)

    def test_encodings_arg(self):
        fname = "foo.py"

        with GitTemporaryDirectory():
            with patch("aider.main.Coder.create") as MockCoder:  # noqa: F841
                with patch("aider.main.InputOutput") as MockSend:

                    def side_effect(*args, **kwargs):
                        self.assertEqual(kwargs["encoding"], "iso-8859-15")
                        return MagicMock()

                    MockSend.side_effect = side_effect

                    main(["--yes", fname, "--encoding", "iso-8859-15"])

    @patch("aider.main.InputOutput")
    @patch("aider.coders.base_coder.Coder.run")
    def test_main_message_adds_to_input_history(self, mock_run, MockInputOutput):
        test_message = "test message"
        mock_io_instance = MockInputOutput.return_value

        main(["--message", test_message], input=DummyInput(), output=DummyOutput())

        mock_io_instance.add_to_input_history.assert_called_once_with(test_message)

    @patch("aider.main.InputOutput")
    @patch("aider.coders.base_coder.Coder.run")
    def test_yes(self, mock_run, MockInputOutput):
        test_message = "test message"

        main(["--yes", "--message", test_message])
        args, kwargs = MockInputOutput.call_args
        self.assertTrue(args[1])

    @patch("aider.main.InputOutput")
    @patch("aider.coders.base_coder.Coder.run")
    def test_default_yes(self, mock_run, MockInputOutput):
        test_message = "test message"

        main(["--message", test_message])
        args, kwargs = MockInputOutput.call_args
        self.assertEqual(args[1], None)

    def test_dark_mode_sets_code_theme(self):
        # Mock Coder.create to capture the configuration
        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--dark-mode", "--no-git"], input=DummyInput(), output=DummyOutput())
            # Ensure Coder.create was called
            MockCoder.assert_called_once()
            # Check if the code_theme setting is for dark mode
            _, kwargs = MockCoder.call_args
            self.assertEqual(kwargs["code_theme"], "monokai")

    def test_light_mode_sets_code_theme(self):
        # Mock Coder.create to capture the configuration
        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--light-mode", "--no-git"], input=DummyInput(), output=DummyOutput())
            # Ensure Coder.create was called
            MockCoder.assert_called_once()
            # Check if the code_theme setting is for light mode
            _, kwargs = MockCoder.call_args
            self.assertEqual(kwargs["code_theme"], "default")

    def create_env_file(self, file_name, content):
        env_file_path = Path(self.tempdir) / file_name
        env_file_path.write_text(content)
        return env_file_path

    def test_env_file_flag_sets_automatic_variable(self):
        env_file_path = self.create_env_file(".env.test", "AIDER_DARK_MODE=True")
        with patch("aider.coders.Coder.create") as MockCoder:
            main(
                ["--env-file", str(env_file_path), "--no-git"],
                input=DummyInput(),
                output=DummyOutput(),
            )
            MockCoder.assert_called_once()
            # Check if the color settings are for dark mode
            _, kwargs = MockCoder.call_args
            self.assertEqual(kwargs["code_theme"], "monokai")

    def test_default_env_file_sets_automatic_variable(self):
        self.create_env_file(".env", "AIDER_DARK_MODE=True")
        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--no-git"], input=DummyInput(), output=DummyOutput())
            # Ensure Coder.create was called
            MockCoder.assert_called_once()
            # Check if the color settings are for dark mode
            _, kwargs = MockCoder.call_args
            self.assertEqual(kwargs["code_theme"], "monokai")

    def test_false_vals_in_env_file(self):
        self.create_env_file(".env", "AIDER_SHOW_DIFFS=off")
        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--no-git"], input=DummyInput(), output=DummyOutput())
            MockCoder.assert_called_once()
            _, kwargs = MockCoder.call_args
            self.assertEqual(kwargs["show_diffs"], False)

    def test_true_vals_in_env_file(self):
        self.create_env_file(".env", "AIDER_SHOW_DIFFS=on")
        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--no-git"], input=DummyInput(), output=DummyOutput())
            MockCoder.assert_called_once()
            _, kwargs = MockCoder.call_args
            self.assertEqual(kwargs["show_diffs"], True)

    def test_verbose_mode_lists_env_vars(self):
        self.create_env_file(".env", "AIDER_DARK_MODE=on")
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            main(["--no-git", "--verbose"], input=DummyInput(), output=DummyOutput())
            output = mock_stdout.getvalue()
            relevant_output = "\n".join(
                line
                for line in output.splitlines()
                if "AIDER_DARK_MODE" in line or "dark_mode" in line
            )  # this bit just helps failing assertions to be easier to read
            self.assertIn("AIDER_DARK_MODE", relevant_output)
            self.assertIn("dark_mode", relevant_output)
            self.assertRegex(relevant_output, r"AIDER_DARK_MODE:\s+on")
            self.assertRegex(relevant_output, r"dark_mode:\s+True")
