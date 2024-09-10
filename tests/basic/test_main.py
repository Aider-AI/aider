import json
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

from aider.coders import Coder
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
        # Fake home directory prevents tests from using the real ~/.aider.conf.yml file:
        self.homedir_obj = IgnorantTemporaryDirectory()
        os.environ["HOME"] = self.homedir_obj.name
        self.input_patcher = patch("builtins.input", return_value=None)
        self.mock_input = self.input_patcher.start()

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tempdir_obj.cleanup()
        self.homedir_obj.cleanup()
        os.environ.clear()
        os.environ.update(self.original_env)
        self.input_patcher.stop()

    def test_main_with_empty_dir_no_files_on_command(self):
        main(["--no-git", "--exit"], input=DummyInput(), output=DummyOutput())

    def test_main_with_emptqy_dir_new_file(self):
        main(["foo.txt", "--yes", "--no-git", "--exit"], input=DummyInput(), output=DummyOutput())
        self.assertTrue(os.path.exists("foo.txt"))

    @patch("aider.repo.GitRepo.get_commit_message", return_value="mock commit message")
    def test_main_with_empty_git_dir_new_file(self, _):
        make_repo()
        main(["--yes", "foo.txt", "--exit"], input=DummyInput(), output=DummyOutput())
        self.assertTrue(os.path.exists("foo.txt"))

    @patch("aider.repo.GitRepo.get_commit_message", return_value="mock commit message")
    def test_main_with_empty_git_dir_new_files(self, _):
        make_repo()
        main(["--yes", "foo.txt", "bar.txt", "--exit"], input=DummyInput(), output=DummyOutput())
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
            ["--yes", str(subdir / "foo.txt"), str(subdir / "bar.txt"), "--exit"],
            input=DummyInput(),
            output=DummyOutput(),
        )
        self.assertTrue((subdir / "foo.txt").exists())
        self.assertTrue((subdir / "bar.txt").exists())

    def test_main_with_git_config_yml(self):
        make_repo()

        Path(".aider.conf.yml").write_text("auto-commits: false\n")
        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--yes"], input=DummyInput(), output=DummyOutput())
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is False

        Path(".aider.conf.yml").write_text("auto-commits: true\n")
        with patch("aider.coders.Coder.create") as MockCoder:
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
        main(["--yes", str(fname), "--exit"], input=DummyInput(), output=DummyOutput())

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

    def test_main_args(self):
        with patch("aider.coders.Coder.create") as MockCoder:
            # --yes will just ok the git repo without blocking on input
            # following calls to main will see the new repo already
            main(["--no-auto-commits", "--yes"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is False

        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--auto-commits"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["auto_commits"] is True

        with patch("aider.coders.Coder.create") as MockCoder:
            main([], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["dirty_commits"] is True
            assert kwargs["auto_commits"] is True

        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--no-dirty-commits"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["dirty_commits"] is False

        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--dirty-commits"], input=DummyInput())
            _, kwargs = MockCoder.call_args
            assert kwargs["dirty_commits"] is True

    def test_env_file_override(self):
        with GitTemporaryDirectory() as git_dir:
            git_dir = Path(git_dir)
            git_env = git_dir / ".env"

            fake_home = git_dir / "fake_home"
            fake_home.mkdir()
            os.environ["HOME"] = str(fake_home)
            home_env = fake_home / ".env"

            cwd = git_dir / "subdir"
            cwd.mkdir()
            os.chdir(cwd)
            cwd_env = cwd / ".env"

            named_env = git_dir / "named.env"

            os.environ["E"] = "existing"
            home_env.write_text("A=home\nB=home\nC=home\nD=home")
            git_env.write_text("A=git\nB=git\nC=git")
            cwd_env.write_text("A=cwd\nB=cwd")
            named_env.write_text("A=named")

            with patch("pathlib.Path.home", return_value=fake_home):
                main(["--yes", "--exit", "--env-file", str(named_env)])

            self.assertEqual(os.environ["A"], "named")
            self.assertEqual(os.environ["B"], "cwd")
            self.assertEqual(os.environ["C"], "git")
            self.assertEqual(os.environ["D"], "home")
            self.assertEqual(os.environ["E"], "existing")

    def test_message_file_flag(self):
        message_file_content = "This is a test message from a file."
        message_file_path = tempfile.mktemp()
        with open(message_file_path, "w", encoding="utf-8") as message_file:
            message_file.write(message_file_content)

        with patch("aider.coders.Coder.create") as MockCoder:
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
            with patch("aider.coders.Coder.create") as MockCoder:  # noqa: F841
                with patch("aider.main.InputOutput") as MockSend:

                    def side_effect(*args, **kwargs):
                        self.assertEqual(kwargs["encoding"], "iso-8859-15")
                        return MagicMock()

                    MockSend.side_effect = side_effect

                    main(["--yes", fname, "--encoding", "iso-8859-15"])

    def test_main_exit_calls_version_check(self):
        with GitTemporaryDirectory():
            with (
                patch("aider.main.check_version") as mock_check_version,
                patch("aider.main.InputOutput") as mock_input_output,
            ):
                main(["--exit"], input=DummyInput(), output=DummyOutput())
                mock_check_version.assert_called_once()
                mock_input_output.assert_called_once()

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
        # Mock InputOutput to capture the configuration
        with patch("aider.main.InputOutput") as MockInputOutput:
            MockInputOutput.return_value.get_input.return_value = None
            main(["--dark-mode", "--no-git", "--exit"], input=DummyInput(), output=DummyOutput())
            # Ensure InputOutput was called
            MockInputOutput.assert_called_once()
            # Check if the code_theme setting is for dark mode
            _, kwargs = MockInputOutput.call_args
            self.assertEqual(kwargs["code_theme"], "monokai")

    def test_light_mode_sets_code_theme(self):
        # Mock InputOutput to capture the configuration
        with patch("aider.main.InputOutput") as MockInputOutput:
            MockInputOutput.return_value.get_input.return_value = None
            main(["--light-mode", "--no-git", "--exit"], input=DummyInput(), output=DummyOutput())
            # Ensure InputOutput was called
            MockInputOutput.assert_called_once()
            # Check if the code_theme setting is for light mode
            _, kwargs = MockInputOutput.call_args
            self.assertEqual(kwargs["code_theme"], "default")

    def create_env_file(self, file_name, content):
        env_file_path = Path(self.tempdir) / file_name
        env_file_path.write_text(content)
        return env_file_path

    def test_env_file_flag_sets_automatic_variable(self):
        env_file_path = self.create_env_file(".env.test", "AIDER_DARK_MODE=True")
        with patch("aider.main.InputOutput") as MockInputOutput:
            MockInputOutput.return_value.get_input.return_value = None
            MockInputOutput.return_value.get_input.confirm_ask = True
            main(
                ["--env-file", str(env_file_path), "--no-git", "--exit"],
                input=DummyInput(),
                output=DummyOutput(),
            )
            MockInputOutput.assert_called_once()
            # Check if the color settings are for dark mode
            _, kwargs = MockInputOutput.call_args
            self.assertEqual(kwargs["code_theme"], "monokai")

    def test_default_env_file_sets_automatic_variable(self):
        self.create_env_file(".env", "AIDER_DARK_MODE=True")
        with patch("aider.main.InputOutput") as MockInputOutput:
            MockInputOutput.return_value.get_input.return_value = None
            MockInputOutput.return_value.get_input.confirm_ask = True
            main(["--no-git", "--exit"], input=DummyInput(), output=DummyOutput())
            # Ensure InputOutput was called
            MockInputOutput.assert_called_once()
            # Check if the color settings are for dark mode
            _, kwargs = MockInputOutput.call_args
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

    def test_lint_option(self):
        with GitTemporaryDirectory() as git_dir:
            # Create a dirty file in the root
            dirty_file = Path("dirty_file.py")
            dirty_file.write_text("def foo():\n    return 'bar'")

            repo = git.Repo(".")
            repo.git.add(str(dirty_file))
            repo.git.commit("-m", "new")

            dirty_file.write_text("def foo():\n    return '!!!!!'")

            # Create a subdirectory
            subdir = Path(git_dir) / "subdir"
            subdir.mkdir()

            # Change to the subdirectory
            os.chdir(subdir)

            # Mock the Linter class
            with patch("aider.linter.Linter.lint") as MockLinter:
                MockLinter.return_value = ""

                # Run main with --lint option
                main(["--lint", "--yes"])

                # Check if the Linter was called with a filename ending in "dirty_file.py"
                # but not ending in "subdir/dirty_file.py"
                MockLinter.assert_called_once()
                called_arg = MockLinter.call_args[0][0]
                self.assertTrue(called_arg.endswith("dirty_file.py"))
                self.assertFalse(called_arg.endswith(f"subdir{os.path.sep}dirty_file.py"))

    def test_verbose_mode_lists_env_vars(self):
        self.create_env_file(".env", "AIDER_DARK_MODE=on")
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            main(["--no-git", "--verbose", "--exit"], input=DummyInput(), output=DummyOutput())
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

    def test_yaml_config_file_loading(self):
        with GitTemporaryDirectory() as git_dir:
            git_dir = Path(git_dir)

            # Create fake home directory
            fake_home = git_dir / "fake_home"
            fake_home.mkdir()
            os.environ["HOME"] = str(fake_home)

            # Create subdirectory as current working directory
            cwd = git_dir / "subdir"
            cwd.mkdir()
            os.chdir(cwd)

            # Create .aider.conf.yml files in different locations
            home_config = fake_home / ".aider.conf.yml"
            git_config = git_dir / ".aider.conf.yml"
            cwd_config = cwd / ".aider.conf.yml"
            named_config = git_dir / "named.aider.conf.yml"

            cwd_config.write_text("model: gpt-4-32k\nmap-tokens: 4096\n")
            git_config.write_text("model: gpt-4\nmap-tokens: 2048\n")
            home_config.write_text("model: gpt-3.5-turbo\nmap-tokens: 1024\n")
            named_config.write_text("model: gpt-4-1106-preview\nmap-tokens: 8192\n")

            with (
                patch("pathlib.Path.home", return_value=fake_home),
                patch("aider.coders.Coder.create") as MockCoder,
            ):
                # Test loading from specified config file
                main(
                    ["--yes", "--exit", "--config", str(named_config)],
                    input=DummyInput(),
                    output=DummyOutput(),
                )
                _, kwargs = MockCoder.call_args
                self.assertEqual(kwargs["main_model"].name, "gpt-4-1106-preview")
                self.assertEqual(kwargs["map_tokens"], 8192)

                # Test loading from current working directory
                main(["--yes", "--exit"], input=DummyInput(), output=DummyOutput())
                _, kwargs = MockCoder.call_args
                print("kwargs:", kwargs)  # Add this line for debugging
                self.assertIn("main_model", kwargs, "main_model key not found in kwargs")
                self.assertEqual(kwargs["main_model"].name, "gpt-4-32k")
                self.assertEqual(kwargs["map_tokens"], 4096)

                # Test loading from git root
                cwd_config.unlink()
                main(["--yes", "--exit"], input=DummyInput(), output=DummyOutput())
                _, kwargs = MockCoder.call_args
                self.assertEqual(kwargs["main_model"].name, "gpt-4")
                self.assertEqual(kwargs["map_tokens"], 2048)

                # Test loading from home directory
                git_config.unlink()
                main(["--yes", "--exit"], input=DummyInput(), output=DummyOutput())
                _, kwargs = MockCoder.call_args
                self.assertEqual(kwargs["main_model"].name, "gpt-3.5-turbo")
                self.assertEqual(kwargs["map_tokens"], 1024)

    def test_map_tokens_option(self):
        with GitTemporaryDirectory():
            with patch("aider.coders.base_coder.RepoMap") as MockRepoMap:
                MockRepoMap.return_value.max_map_tokens = 0
                main(
                    ["--model", "gpt-4", "--map-tokens", "0", "--exit", "--yes"],
                    input=DummyInput(),
                    output=DummyOutput(),
                )
                MockRepoMap.assert_not_called()

    def test_map_tokens_option_with_non_zero_value(self):
        with GitTemporaryDirectory():
            with patch("aider.coders.base_coder.RepoMap") as MockRepoMap:
                MockRepoMap.return_value.max_map_tokens = 1000
                main(
                    ["--model", "gpt-4", "--map-tokens", "1000", "--exit", "--yes"],
                    input=DummyInput(),
                    output=DummyOutput(),
                )
                MockRepoMap.assert_called_once()

    def test_read_option(self):
        with GitTemporaryDirectory():
            test_file = "test_file.txt"
            Path(test_file).touch()

            coder = main(
                ["--read", test_file, "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )

            self.assertIn(str(Path(test_file).resolve()), coder.abs_read_only_fnames)

    def test_read_option_with_external_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as external_file:
            external_file.write("External file content")
            external_file_path = external_file.name

        try:
            with GitTemporaryDirectory():
                coder = main(
                    ["--read", external_file_path, "--exit", "--yes"],
                    input=DummyInput(),
                    output=DummyOutput(),
                    return_coder=True,
                )

                real_external_file_path = os.path.realpath(external_file_path)
                self.assertIn(real_external_file_path, coder.abs_read_only_fnames)
        finally:
            os.unlink(external_file_path)

    def test_model_metadata_file(self):
        with GitTemporaryDirectory():
            metadata_file = Path(".aider.model.metadata.json")

            # must be a fully qualified model name: provider/...
            metadata_content = {"deepseek/deepseek-chat": {"max_input_tokens": 1234}}
            metadata_file.write_text(json.dumps(metadata_content))

            coder = main(
                [
                    "--model",
                    "deepseek/deepseek-chat",
                    "--model-metadata-file",
                    str(metadata_file),
                    "--exit",
                    "--yes",
                ],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )

            self.assertEqual(coder.main_model.info["max_input_tokens"], 1234)

    def test_sonnet_and_cache_options(self):
        with GitTemporaryDirectory():
            with patch("aider.coders.base_coder.RepoMap") as MockRepoMap:
                mock_repo_map = MagicMock()
                mock_repo_map.max_map_tokens = 1000  # Set a specific value
                MockRepoMap.return_value = mock_repo_map

                main(
                    ["--sonnet", "--cache-prompts", "--exit", "--yes"],
                    input=DummyInput(),
                    output=DummyOutput(),
                )

                MockRepoMap.assert_called_once()
                call_args, call_kwargs = MockRepoMap.call_args
                self.assertEqual(
                    call_kwargs.get("refresh"), "files"
                )  # Check the 'refresh' keyword argument

    def test_sonnet_and_cache_prompts_options(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--sonnet", "--cache-prompts", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )

            self.assertTrue(coder.add_cache_headers)

    def test_4o_and_cache_options(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--4o", "--cache-prompts", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )

            self.assertFalse(coder.add_cache_headers)

    def test_return_coder(self):
        with GitTemporaryDirectory():
            result = main(
                ["--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )
            self.assertIsInstance(result, Coder)

            result = main(
                ["--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=False,
            )
            self.assertIsNone(result)

    def test_map_mul_option(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--map-mul", "5", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )
            self.assertIsInstance(coder, Coder)
            self.assertEqual(coder.repo_map.map_mul_no_files, 5)

    def test_suggest_shell_commands_default(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )
            self.assertTrue(coder.suggest_shell_commands)

    def test_suggest_shell_commands_disabled(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--no-suggest-shell-commands", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )
            self.assertFalse(coder.suggest_shell_commands)

    def test_suggest_shell_commands_enabled(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--suggest-shell-commands", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )
            self.assertTrue(coder.suggest_shell_commands)

    def test_chat_language_spanish(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--chat-language", "Spanish", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )
            system_info = coder.get_platform_info()
            self.assertIn("Spanish", system_info)

    @patch("git.Repo.init")
    def test_main_exit_with_git_command_not_found(self, mock_git_init):
        mock_git_init.side_effect = git.exc.GitCommandNotFound("git", "Command 'git' not found")

        try:
            result = main(["--exit", "--yes"], input=DummyInput(), output=DummyOutput())
        except Exception as e:
            self.fail(f"main() raised an unexpected exception: {e}")

        self.assertIsNone(result, "main() should return None when called with --exit")
