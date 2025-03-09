import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput

from aider.deprecated import handle_deprecated_model_args
from aider.dump import dump  # noqa
from aider.main import main


class TestDeprecated(TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["OPENAI_API_KEY"] = "deadbeef"
        os.environ["AIDER_CHECK_UPDATE"] = "false"
        os.environ["AIDER_ANALYTICS"] = "false"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    @patch("aider.io.InputOutput.tool_warning")
    @patch("aider.io.InputOutput.offer_url")
    def test_deprecated_args_show_warnings(self, mock_offer_url, mock_tool_warning):
        # Prevent URL launches during tests
        mock_offer_url.return_value = False
        # Test all deprecated flags to ensure they show warnings
        deprecated_flags = [
            "--opus",
            "--sonnet",
            "--haiku",
            "--4",
            "-4",
            "--4o",
            "--mini",
            "--4-turbo",
            "--35turbo",
            "--35-turbo",
            "--3",
            "-3",
            "--deepseek",
            "--o1-mini",
            "--o1-preview",
        ]

        for flag in deprecated_flags:
            mock_tool_warning.reset_mock()

            with patch("aider.models.Model"), self.subTest(flag=flag):
                main(
                    [flag, "--no-git", "--exit", "--yes"], input=DummyInput(), output=DummyOutput()
                )

                # Look for the deprecation warning in all calls
                deprecation_warning = None
                dump(flag)
                dump(mock_tool_warning.call_args_list)
                for call_args in mock_tool_warning.call_args_list:
                    dump(call_args)
                    if "deprecated" in call_args[0][0]:
                        deprecation_warning = call_args[0][0]
                        break

                self.assertIsNotNone(
                    deprecation_warning, f"No deprecation warning found for {flag}"
                )
                warning_msg = deprecation_warning

                self.assertIn("deprecated", warning_msg)
                self.assertIn("use --model", warning_msg.lower())

    @patch("aider.io.InputOutput.tool_warning")
    @patch("aider.io.InputOutput.offer_url")
    def test_model_alias_in_warning(self, mock_offer_url, mock_tool_warning):
        # Prevent URL launches during tests
        mock_offer_url.return_value = False
        # Test that the warning uses the model alias if available
        with patch("aider.models.MODEL_ALIASES", {"gpt4": "gpt-4-0613"}):
            with patch("aider.models.Model"):
                main(
                    ["--4", "--no-git", "--exit", "--yes"], input=DummyInput(), output=DummyOutput()
                )

                # Look for the deprecation warning in all calls
                deprecation_warning = None
                for call_args in mock_tool_warning.call_args_list:
                    if "deprecated" in call_args[0][0] and "--model gpt4" in call_args[0][0]:
                        deprecation_warning = call_args[0][0]
                        break

                self.assertIsNotNone(
                    deprecation_warning, "No deprecation warning with model alias found"
                )
                warning_msg = deprecation_warning
                self.assertIn("--model gpt4", warning_msg)
                self.assertNotIn("--model gpt-4-0613", warning_msg)

    def test_model_is_set_correctly(self):
        test_cases = [
            ("opus", "claude-3-opus-20240229"),
            ("sonnet", "anthropic/claude-3-7-sonnet-20250219"),
            ("haiku", "claude-3-5-haiku-20241022"),
            ("4", "gpt-4-0613"),
            # Testing the dash variant with underscore in attribute name
            ("4o", "gpt-4o"),
            ("mini", "gpt-4o-mini"),
            ("4_turbo", "gpt-4-1106-preview"),
            ("35turbo", "gpt-3.5-turbo"),
            ("deepseek", "deepseek/deepseek-chat"),
            ("o1_mini", "o1-mini"),
            ("o1_preview", "o1-preview"),
        ]

        for flag, expected_model in test_cases:
            print(flag, expected_model)

            with self.subTest(flag=flag):
                # Create a mock IO instance
                mock_io = MagicMock()

                # Create args with ONLY the current flag set to True
                args = MagicMock()
                args.model = None

                # Ensure all flags are False by default
                for test_flag, _ in test_cases:
                    setattr(args, test_flag, False)

                # Set only the current flag to True
                setattr(args, flag, True)

                dump(args)

                # Call the handle_deprecated_model_args function
                handle_deprecated_model_args(args, mock_io)

                # Check that args.model was set to the expected model
                self.assertEqual(args.model, expected_model)
