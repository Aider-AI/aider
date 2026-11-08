from io import StringIO
import os
import threading
from unittest import TestCase
from unittest.mock import MagicMock, patch

from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput

from aider import urls
from aider.llm import LazyLiteLLM, litellm
from aider.main import load_slow_imports, main


def _create_mock_litellm():
    mock_mod = MagicMock()
    mock_mod.get_model_info.return_value = {"max_input_tokens": 4096}
    mock_mod.validate_environment.return_value = {
        "keys_in_environment": [],
        "missing_keys": [],
    }
    return mock_mod


class TestLazyLiteLLM(TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ["AIDER_CHECK_UPDATE"] = "false"
        os.environ["AIDER_ANALYTICS"] = "false"
        LazyLiteLLM._lazy_module = None
        litellm._lazy_module = None

    def tearDown(self):
        LazyLiteLLM._lazy_module = None
        litellm._lazy_module = None
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch("aider.llm._import_litellm")
    def test_lazy_load_normal_startup(self, mock_import):
        mock_module = _create_mock_litellm()
        mock_module.some_attr = "test_value"
        mock_import.return_value = mock_module

        lazy = LazyLiteLLM()
        self.assertIsNone(lazy._lazy_module)

        # Accessing an attribute triggers loading
        value = lazy.some_attr

        self.assertEqual(value, "test_value")
        self.assertIs(lazy._lazy_module, mock_module)
        mock_import.assert_called_once()
        self.assertTrue(mock_module.suppress_debug_info)
        self.assertFalse(mock_module.set_verbose)
        self.assertTrue(mock_module.drop_params)
        mock_module._logging._disable_debugging.assert_called_once()

    @patch("aider.llm._import_litellm")
    def test_missing_litellm(self, mock_import):
        err = ModuleNotFoundError("No module named 'litellm'", name="litellm")
        mock_import.side_effect = err

        lazy = LazyLiteLLM()
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            with self.assertRaises(SystemExit) as cm:
                _ = lazy.some_attr

            self.assertEqual(cm.exception.code, 1)
            stderr_output = mock_stderr.getvalue()
            self.assertIn("No module named 'litellm'", stderr_output)
            self.assertIn("Did you install aider properly?", stderr_output)
            self.assertIn(urls.install_properly, stderr_output)

    @patch("aider.llm._import_litellm")
    def test_unrelated_module_not_found_error_is_reraised(self, mock_import):
        err = ModuleNotFoundError("No module named 'unrelated_module'", name="unrelated_module")
        mock_import.side_effect = err

        lazy = LazyLiteLLM()
        with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
            with self.assertRaises(ModuleNotFoundError) as cm:
                _ = lazy.some_attr

            self.assertEqual(cm.exception.name, "unrelated_module")
            # Unrelated error must not be misidentified as aiohttp or litellm
            self.assertEqual(mock_stderr.getvalue(), "")

    @patch("aider.llm._import_litellm")
    def test_missing_aiohttp_prompt_no_exits_gracefully(self, mock_import):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        mock_import.side_effect = err

        lazy = LazyLiteLLM()
        with patch("builtins.input", return_value="N"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with self.assertRaises(SystemExit) as cm:
                    _ = lazy.some_attr

                self.assertEqual(cm.exception.code, 1)
                stdout_val = mock_stdout.getvalue()
                self.assertIn("Missing Required Dependency", stdout_val)
                self.assertIn("The 'aiohttp' module is not installed.", stdout_val)
                self.assertIn("This module is required to run Aider with LiteLLM.", stdout_val)
                self.assertIn("Would you like to install it now?", stdout_val)
                self.assertIn("[Y] Yes — Install aiohttp", stdout_val)
                self.assertIn("[N] No — Exit Aider", stdout_val)

    @patch("aider.utils.run_install")
    @patch("aider.llm._import_litellm")
    def test_missing_aiohttp_prompt_yes_installs_and_retries_successfully(
        self, mock_import, mock_run_install
    ):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        mock_module = _create_mock_litellm()
        mock_module.some_attr = "recovered_value"

        installed = False

        def fake_import():
            if not installed:
                raise err
            return mock_module

        def do_install(*args, **kwargs):
            nonlocal installed
            installed = True
            return True, "Installed"

        mock_import.side_effect = fake_import
        mock_run_install.side_effect = do_install

        lazy = LazyLiteLLM()
        with patch("builtins.input", return_value="Y"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                value = lazy.some_attr

                self.assertEqual(value, "recovered_value")
                mock_run_install.assert_called_once()
                stdout_val = mock_stdout.getvalue()
                self.assertIn("Missing Required Dependency", stdout_val)
                self.assertIn("[Y] Yes — Install aiohttp", stdout_val)
                self.assertIn("Loading aiohttp...", stdout_val)
                self.assertIn("Loading litellm...", stdout_val)

    @patch("aider.utils.run_install", return_value=(False, "Failed to connect to index"))
    @patch("aider.llm._import_litellm")
    def test_missing_aiohttp_prompt_yes_installation_fails(
        self, mock_import, mock_run_install
    ):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        mock_import.side_effect = err

        lazy = LazyLiteLLM()
        with patch("builtins.input", return_value="Y"):
            with patch("sys.stdout", new_callable=StringIO):
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with self.assertRaises(SystemExit) as cm:
                        _ = lazy.some_attr

                    self.assertEqual(cm.exception.code, 1)
                    mock_run_install.assert_called_once()
                    stderr_val = mock_stderr.getvalue()
                    self.assertIn("Installation failed.", stderr_val)
                    self.assertIn("Please install 'aiohttp' manually using:", stderr_val)
                    self.assertIn("pip install", stderr_val)
                    self.assertIn(urls.install_properly, stderr_val)

    @patch("aider.utils.run_install", return_value=(True, "Installed"))
    @patch("aider.llm._import_litellm")
    def test_missing_aiohttp_retry_fails_without_infinite_loop(
        self, mock_import, mock_run_install
    ):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        retry_err = ModuleNotFoundError("No module named 'litellm'", name="litellm")
        mock_import.side_effect = [err, retry_err]

        lazy = LazyLiteLLM()
        with patch("builtins.input", return_value="Y"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with self.assertRaises(SystemExit) as cm:
                        _ = lazy.some_attr

                    self.assertEqual(cm.exception.code, 1)
                    self.assertEqual(mock_import.call_count, 2)  # Initial try + exactly 1 retry
                    stdout_val = mock_stdout.getvalue()
                    self.assertIn("Loading aiohttp...", stdout_val)
                    self.assertIn("Loading litellm...", stdout_val)
                    stderr_val = mock_stderr.getvalue()
                    self.assertIn("No module named 'litellm'", stderr_val)
                    self.assertIn("Did you install aider properly?", stderr_val)

    @patch("aider.utils.run_install", return_value=(True, "Installed"))
    @patch("aider.llm._import_litellm")
    def test_missing_aiohttp_retry_fails_with_aiohttp_error(
        self, mock_import, mock_run_install
    ):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        retry_err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        mock_import.side_effect = [err, retry_err]

        lazy = LazyLiteLLM()
        with patch("builtins.input", return_value="Y"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with self.assertRaises(SystemExit) as cm:
                        _ = lazy.some_attr

                    self.assertEqual(cm.exception.code, 1)
                    self.assertEqual(mock_import.call_count, 2)
                    stdout_val = mock_stdout.getvalue()
                    self.assertIn("Loading aiohttp...", stdout_val)
                    self.assertIn("Loading litellm...", stdout_val)
                    stderr_val = mock_stderr.getvalue()
                    self.assertIn("No module named 'aiohttp'", stderr_val)
                    self.assertIn("Did you install aider properly?", stderr_val)

    @patch("aider.utils.run_install", return_value=(True, "Installed"))
    @patch("aider.llm._import_litellm")
    def test_missing_aiohttp_retry_unrelated_module_not_found_error_is_reraised(
        self, mock_import, mock_run_install
    ):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        retry_err = ModuleNotFoundError(
            "No module named 'unrelated_module'", name="unrelated_module"
        )
        mock_import.side_effect = [err, retry_err]

        lazy = LazyLiteLLM()
        with patch("builtins.input", return_value="Y"):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                    with self.assertRaises(ModuleNotFoundError) as cm:
                        _ = lazy.some_attr

                    self.assertEqual(cm.exception.name, "unrelated_module")
                    self.assertEqual(mock_import.call_count, 2)
                    stdout_val = mock_stdout.getvalue()
                    self.assertIn("Loading aiohttp...", stdout_val)
                    self.assertIn("Loading litellm...", stdout_val)
                    # Unrelated error must not be misidentified as litellm/aiohttp error
                    self.assertEqual(mock_stderr.getvalue(), "")

    @patch("aider.llm._import_litellm")
    def test_background_thread_does_not_prompt_and_swallows(self, mock_import):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        mock_import.side_effect = err

        # Run load_slow_imports in a background thread as main.py does
        thread_error = None

        def run_thread():
            nonlocal thread_error
            try:
                load_slow_imports(swallow=True)
            except Exception as e:
                thread_error = e

        thread = threading.Thread(target=run_thread)
        thread.start()
        thread.join(timeout=5)

        self.assertFalse(thread.is_alive())
        self.assertIsNone(thread_error)  # Exception was swallowed cleanly in thread

    @patch("aider.main.is_first_run_of_new_version", return_value=False)
    @patch("aider.utils.run_install")
    @patch("aider.llm._import_litellm")
    def test_main_startup_with_missing_aiohttp_user_accepts_install(
        self, mock_import, mock_run_install, mock_first_run
    ):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        mock_module = _create_mock_litellm()

        installed = False

        def fake_import():
            if not installed:
                raise err
            return mock_module

        def do_install(*args, **kwargs):
            nonlocal installed
            installed = True
            return True, "Installed"

        mock_import.side_effect = fake_import
        mock_run_install.side_effect = do_install

        with patch("builtins.input", return_value="y"):
            status = main(
                ["--model", "ollama/llama3", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
            )
            self.assertIn(status, (0, None))
            mock_run_install.assert_called_once()

    @patch("aider.main.is_first_run_of_new_version", return_value=False)
    @patch("aider.llm._import_litellm")
    def test_main_startup_with_missing_aiohttp_user_declines_install(
        self, mock_import, mock_first_run
    ):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        mock_import.side_effect = err

        with patch("builtins.input", return_value="n"):
            with self.assertRaises(SystemExit) as cm:
                main(
                    ["--model", "ollama/llama3", "--exit", "--yes"],
                    input=DummyInput(),
                    output=DummyOutput(),
                )
            self.assertEqual(cm.exception.code, 1)

    @patch("aider.main.is_first_run_of_new_version", return_value=True)
    @patch("aider.utils.run_install")
    @patch("aider.llm._import_litellm")
    def test_first_run_synchronous_startup_with_missing_aiohttp(
        self, mock_import, mock_run_install, mock_first_run
    ):
        err = ModuleNotFoundError("No module named 'aiohttp'", name="aiohttp")
        mock_module = _create_mock_litellm()

        installed = False

        def fake_import():
            if not installed:
                raise err
            return mock_module

        def do_install(*args, **kwargs):
            nonlocal installed
            installed = True
            return True, "Installed"

        mock_import.side_effect = fake_import
        mock_run_install.side_effect = do_install

        with patch("builtins.input", return_value="y"):
            status = main(
                ["--model", "ollama/llama3", "--exit", "--yes"],
                input=DummyInput(),
                output=DummyOutput(),
            )
            self.assertIn(status, (0, None))
            mock_run_install.assert_called_once()
