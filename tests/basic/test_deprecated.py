import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

from prompt_toolkit.input import DummyInput
from prompt_toolkit.output import DummyOutput

from aider.main import main
from aider.deprecated import handle_deprecated_model_args


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
    def test_deprecated_args_show_warnings(self, mock_tool_warning):
        # Test all deprecated flags to ensure they show warnings
        deprecated_flags = [
            "--opus", 
            "--sonnet", 
            "--haiku", 
            "--4", 
            "--4o", 
            "--mini", 
            "--4-turbo", 
            "--3", 
            "--deepseek", 
            "--o1-mini", 
            "--o1-preview"
        ]
        
        for flag in deprecated_flags:
            mock_tool_warning.reset_mock()
            
            with patch("aider.models.Model"), self.subTest(flag=flag):
                main([flag, "--no-git", "--exit", "--yes"], input=DummyInput(), output=DummyOutput())
                
                mock_tool_warning.assert_called_once()
                warning_msg = mock_tool_warning.call_args[0][0]
                
                # Remove any leading hyphens for the comparison
                flag_in_msg = flag.lstrip('-')
                
                self.assertIn(flag_in_msg, warning_msg)
                self.assertIn("deprecated", warning_msg)
                self.assertIn("use --model", warning_msg.lower())

    @patch("aider.io.InputOutput.tool_warning")
    def test_model_alias_in_warning(self, mock_tool_warning):
        # Test that the warning uses the model alias if available
        with patch("aider.models.MODEL_ALIASES", {"gpt4": "gpt-4-0613"}):
            with patch("aider.models.Model"):
                main(["--4", "--no-git", "--exit", "--yes"], input=DummyInput(), output=DummyOutput())
                
                mock_tool_warning.assert_called_once()
                warning_msg = mock_tool_warning.call_args[0][0]
                self.assertIn("--model gpt4", warning_msg)
                self.assertNotIn("--model gpt-4-0613", warning_msg)

    def test_model_is_set_correctly(self):
        test_cases = [
            ("opus", "claude-3-opus-20240229"),
            ("sonnet", "anthropic/claude-3-7-sonnet-20250219"),
            ("haiku", "claude-3-5-haiku-20241022"),
            ("4", "gpt-4-0613"),
            ("4o", "gpt-4o"),
            ("mini", "gpt-4o-mini"),
            ("4_turbo", "gpt-4-1106-preview"),
            ("35turbo", "gpt-3.5-turbo"),
            ("deepseek", "deepseek/deepseek-chat"),
            ("o1_mini", "o1-mini"),
            ("o1_preview", "o1-preview"),
        ]
        
        for flag, expected_model in test_cases:
            with self.subTest(flag=flag):
                # Create a mock IO instance
                mock_io = MagicMock()
                
                # Create args with the flag set to True
                args = MagicMock()
                args.model = None
                setattr(args, flag, True)
                
                # Call the handle_deprecated_model_args function
                handle_deprecated_model_args(args, mock_io)
                
                # Check that args.model was set to the expected model
                self.assertEqual(args.model, expected_model)
