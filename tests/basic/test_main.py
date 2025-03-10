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
        os.environ["AIDER_CHECK_UPDATE"] = "false"
        os.environ["AIDER_ANALYTICS"] = "false"
        self.original_cwd = os.getcwd()
        self.tempdir_obj = IgnorantTemporaryDirectory()
        self.tempdir = self.tempdir_obj.name
        os.chdir(self.tempdir)
        # Fake home directory prevents tests from using the real ~/.aider.conf.yml file:
        self.homedir_obj = IgnorantTemporaryDirectory()
        os.environ["HOME"] = self.homedir_obj.name
        self.input_patcher = patch("builtins.input", return_value=None)
        self.mock_input = self.input_patcher.start()
        self.webbrowser_patcher = patch("aider.io.webbrowser.open")
        self.mock_webbrowser = self.webbrowser_patcher.start()

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.tempdir_obj.cleanup()
        self.homedir_obj.cleanup()
        os.environ.clear()
        os.environ.update(self.original_env)
        self.input_patcher.stop()
        self.webbrowser_patcher.stop()

    def test_main_with_empty_dir_no_files_on_command(self):
        main(["--no-git", "--exit", "--yes"], input=DummyInput(), output=DummyOutput())

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

            # Test without .env file present
            gitignore.write_text("one\ntwo\n")
            check_gitignore(cwd, io)
            self.assertEqual("one\ntwo\n.aider*\n", gitignore.read_text())

            # Test with .env file present
            env_file = cwd / ".env"
            env_file.touch()
            check_gitignore(cwd, io)
            self.assertEqual("one\ntwo\n.aider*\n.env\n", gitignore.read_text())
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
                main(["--exit", "--check-update"], input=DummyInput(), output=DummyOutput())
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
            main(["--no-git", "--yes"], input=DummyInput(), output=DummyOutput())
            MockCoder.assert_called_once()
            _, kwargs = MockCoder.call_args
            self.assertEqual(kwargs["show_diffs"], False)

    def test_true_vals_in_env_file(self):
        self.create_env_file(".env", "AIDER_SHOW_DIFFS=on")
        with patch("aider.coders.Coder.create") as MockCoder:
            main(["--no-git", "--yes"], input=DummyInput(), output=DummyOutput())
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
            main(
                ["--no-git", "--verbose", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
            )
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
        # Re-init so we don't have old data lying around from earlier test cases
        from aider import models

        models.model_info_manager = models.ModelInfoManager()

        from aider.llm import litellm

        litellm._lazy_module = None

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

    def test_detect_urls_default(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )
            self.assertTrue(coder.detect_urls)

    def test_detect_urls_disabled(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--no-detect-urls", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )
            self.assertFalse(coder.detect_urls)

    def test_detect_urls_enabled(self):
        with GitTemporaryDirectory():
            coder = main(
                ["--detect-urls", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
                return_coder=True,
            )
            self.assertTrue(coder.detect_urls)

    @patch("aider.models.ModelInfoManager.set_verify_ssl")
    def test_no_verify_ssl_sets_model_info_manager(self, mock_set_verify_ssl):
        with GitTemporaryDirectory():
            # Mock Model class to avoid actual model initialization
            with patch("aider.models.Model") as mock_model:
                # Configure the mock to avoid the TypeError
                mock_model.return_value.info = {}
                mock_model.return_value.name = "gpt-4"  # Add a string name
                mock_model.return_value.validate_environment.return_value = {
                    "missing_keys": [],
                    "keys_in_environment": [],
                }

                # Mock fuzzy_match_models to avoid string operations on MagicMock
                with patch("aider.models.fuzzy_match_models", return_value=[]):
                    main(
                        ["--no-verify-ssl", "--exit", "--yes"],
                        input=DummyInput(),
                        output=DummyOutput(),
                    )
                mock_set_verify_ssl.assert_called_once_with(False)

    def test_pytest_env_vars(self):
        # Verify that environment variables from pytest.ini are properly set
        self.assertEqual(os.environ.get("AIDER_ANALYTICS"), "false")

    def test_set_env_single(self):
        # Test setting a single environment variable
        with GitTemporaryDirectory():
            main(["--set-env", "TEST_VAR=test_value", "--exit", "--yes"])
            self.assertEqual(os.environ.get("TEST_VAR"), "test_value")

    def test_set_env_multiple(self):
        # Test setting multiple environment variables
        with GitTemporaryDirectory():
            main(
                [
                    "--set-env",
                    "TEST_VAR1=value1",
                    "--set-env",
                    "TEST_VAR2=value2",
                    "--exit",
                    "--yes",
                ]
            )
            self.assertEqual(os.environ.get("TEST_VAR1"), "value1")
            self.assertEqual(os.environ.get("TEST_VAR2"), "value2")

    def test_set_env_with_spaces(self):
        # Test setting env var with spaces in value
        with GitTemporaryDirectory():
            main(["--set-env", "TEST_VAR=test value with spaces", "--exit", "--yes"])
            self.assertEqual(os.environ.get("TEST_VAR"), "test value with spaces")

    def test_set_env_invalid_format(self):
        # Test invalid format handling
        with GitTemporaryDirectory():
            result = main(["--set-env", "INVALID_FORMAT", "--exit", "--yes"])
            self.assertEqual(result, 1)

    def test_api_key_single(self):
        # Test setting a single API key
        with GitTemporaryDirectory():
            main(["--api-key", "anthropic=test-key", "--exit", "--yes"])
            self.assertEqual(os.environ.get("ANTHROPIC_API_KEY"), "test-key")

    def test_api_key_multiple(self):
        # Test setting multiple API keys
        with GitTemporaryDirectory():
            main(["--api-key", "anthropic=key1", "--api-key", "openai=key2", "--exit", "--yes"])
            self.assertEqual(os.environ.get("ANTHROPIC_API_KEY"), "key1")
            self.assertEqual(os.environ.get("OPENAI_API_KEY"), "key2")

    def test_api_key_invalid_format(self):
        # Test invalid format handling
        with GitTemporaryDirectory():
            result = main(["--api-key", "INVALID_FORMAT", "--exit", "--yes"])
            self.assertEqual(result, 1)

    def test_git_config_include(self):
        # Test that aider respects git config includes for user.name and user.email
        with GitTemporaryDirectory() as git_dir:
            git_dir = Path(git_dir)

            # Create an includable config file with user settings
            include_config = git_dir / "included.gitconfig"
            include_config.write_text(
                "[user]\n    name = Included User\n    email = included@example.com\n"
            )

            # Set up main git config to include the other file
            repo = git.Repo(git_dir)
            include_path = str(include_config).replace("\\", "/")
            repo.git.config("--local", "include.path", str(include_path))

            # Verify the config is set up correctly using git command
            self.assertEqual(repo.git.config("user.name"), "Included User")
            self.assertEqual(repo.git.config("user.email"), "included@example.com")

            # Manually check the git config file to confirm include directive
            git_config_path = git_dir / ".git" / "config"
            git_config_content = git_config_path.read_text()

            # Run aider and verify it doesn't change the git config
            main(["--yes", "--exit"], input=DummyInput(), output=DummyOutput())

            # Check that the user settings are still the same using git command
            repo = git.Repo(git_dir)  # Re-open repo to ensure we get fresh config
            self.assertEqual(repo.git.config("user.name"), "Included User")
            self.assertEqual(repo.git.config("user.email"), "included@example.com")

            # Manually check the git config file again to ensure it wasn't modified
            git_config_content_after = git_config_path.read_text()
            self.assertEqual(git_config_content, git_config_content_after)

    def test_git_config_include_directive(self):
        # Test that aider respects the include directive in git config
        with GitTemporaryDirectory() as git_dir:
            git_dir = Path(git_dir)

            # Create an includable config file with user settings
            include_config = git_dir / "included.gitconfig"
            include_config.write_text(
                "[user]\n    name = Directive User\n    email = directive@example.com\n"
            )

            # Set up main git config with include directive
            git_config = git_dir / ".git" / "config"
            # Use normalized path with forward slashes for git config
            include_path = str(include_config).replace("\\", "/")
            with open(git_config, "a") as f:
                f.write(f"\n[include]\n    path = {include_path}\n")

            # Read the modified config file
            modified_config_content = git_config.read_text()

            # Verify the include directive was added correctly
            self.assertIn("[include]", modified_config_content)

            # Verify the config is set up correctly using git command
            repo = git.Repo(git_dir)
            self.assertEqual(repo.git.config("user.name"), "Directive User")
            self.assertEqual(repo.git.config("user.email"), "directive@example.com")

            # Run aider and verify it doesn't change the git config
            main(["--yes", "--exit"], input=DummyInput(), output=DummyOutput())

            # Check that the git config file wasn't modified
            config_after_aider = git_config.read_text()
            self.assertEqual(modified_config_content, config_after_aider)

            # Check that the user settings are still the same using git command
            repo = git.Repo(git_dir)  # Re-open repo to ensure we get fresh config
            self.assertEqual(repo.git.config("user.name"), "Directive User")
            self.assertEqual(repo.git.config("user.email"), "directive@example.com")

    def test_invalid_edit_format(self):
        with GitTemporaryDirectory():
            with patch("aider.io.InputOutput.offer_url") as mock_offer_url:
                result = main(
                    ["--edit-format", "not-a-real-format", "--exit", "--yes"],
                    input=DummyInput(),
                    output=DummyOutput(),
                )
                self.assertEqual(result, 1)  # main() should return 1 on error
                mock_offer_url.assert_called_once()
                args, _ = mock_offer_url.call_args
                self.assertEqual(args[0], "https://aider.chat/docs/more/edit-formats.html")

    def test_default_model_selection(self):
        with GitTemporaryDirectory():
            # Test Anthropic API key
            os.environ["ANTHROPIC_API_KEY"] = "test-key"
            coder = main(
                ["--exit", "--yes"], input=DummyInput(), output=DummyOutput(), return_coder=True
            )
            self.assertIn("sonnet", coder.main_model.name.lower())
            del os.environ["ANTHROPIC_API_KEY"]

            # Test DeepSeek API key
            os.environ["DEEPSEEK_API_KEY"] = "test-key"
            coder = main(
                ["--exit", "--yes"], input=DummyInput(), output=DummyOutput(), return_coder=True
            )
            self.assertIn("deepseek", coder.main_model.name.lower())
            del os.environ["DEEPSEEK_API_KEY"]

            # Test OpenRouter API key
            os.environ["OPENROUTER_API_KEY"] = "test-key"
            coder = main(
                ["--exit", "--yes"], input=DummyInput(), output=DummyOutput(), return_coder=True
            )
            self.assertIn("openrouter/anthropic/claude", coder.main_model.name.lower())
            del os.environ["OPENROUTER_API_KEY"]

            # Test OpenAI API key
            os.environ["OPENAI_API_KEY"] = "test-key"
            coder = main(
                ["--exit", "--yes"], input=DummyInput(), output=DummyOutput(), return_coder=True
            )
            self.assertIn("gpt-4", coder.main_model.name.lower())
            del os.environ["OPENAI_API_KEY"]

            # Test Gemini API key
            os.environ["GEMINI_API_KEY"] = "test-key"
            coder = main(
                ["--exit", "--yes"], input=DummyInput(), output=DummyOutput(), return_coder=True
            )
            self.assertIn("flash", coder.main_model.name.lower())
            del os.environ["GEMINI_API_KEY"]

            # Test no API keys
            result = main(["--exit", "--yes"], input=DummyInput(), output=DummyOutput())
            self.assertEqual(result, 1)

    def test_model_precedence(self):
        with GitTemporaryDirectory():
            # Test that earlier API keys take precedence
            os.environ["ANTHROPIC_API_KEY"] = "test-key"
            os.environ["OPENAI_API_KEY"] = "test-key"
            coder = main(
                ["--exit", "--yes"], input=DummyInput(), output=DummyOutput(), return_coder=True
            )
            self.assertIn("sonnet", coder.main_model.name.lower())
            del os.environ["ANTHROPIC_API_KEY"]
            del os.environ["OPENAI_API_KEY"]

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

    def test_reasoning_effort_option(self):
        coder = main(
            ["--reasoning-effort", "3", "--yes", "--exit"],
            input=DummyInput(),
            output=DummyOutput(),
            return_coder=True,
        )
        self.assertEqual(
            coder.main_model.extra_params.get("extra_body", {}).get("reasoning_effort"), "3"
        )
