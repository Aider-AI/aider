import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aider.dump import dump  # noqa: F401
from aider.io import AutoCompleter, ConfirmGroup, InputOutput
from aider.utils import ChdirTemporaryDirectory


class TestInputOutput(unittest.TestCase):
    def test_no_color_environment_variable(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            io = InputOutput()
            self.assertFalse(io.pretty)

    def test_autocompleter_with_non_existent_file(self):
        root = ""
        rel_fnames = ["non_existent_file.txt"]
        addable_rel_fnames = []
        commands = None
        autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")
        self.assertEqual(autocompleter.words, set(rel_fnames))

    def test_autocompleter_with_unicode_file(self):
        with ChdirTemporaryDirectory():
            root = ""
            fname = "file.py"
            rel_fnames = [fname]
            addable_rel_fnames = []
            commands = None
            autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")
            self.assertEqual(autocompleter.words, set(rel_fnames))

            Path(fname).write_text("def hello(): pass\n")
            autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")
            autocompleter.tokenize()
            dump(autocompleter.words)
            self.assertEqual(autocompleter.words, set(rel_fnames + [("hello", "`hello`")]))

            encoding = "utf-16"
            some_content_which_will_error_if_read_with_encoding_utf8 = "ÅÍÎÏ".encode(encoding)
            with open(fname, "wb") as f:
                f.write(some_content_which_will_error_if_read_with_encoding_utf8)

            autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")
            self.assertEqual(autocompleter.words, set(rel_fnames))

    @patch("builtins.input", return_value="test input")
    def test_get_input_is_a_directory_error(self, mock_input):
        io = InputOutput(pretty=False)  # Windows tests throw UnicodeDecodeError
        root = "/"
        rel_fnames = ["existing_file.txt"]
        addable_rel_fnames = ["new_file.txt"]
        commands = MagicMock()

        # Simulate IsADirectoryError
        with patch("aider.io.open", side_effect=IsADirectoryError):
            result = io.get_input(root, rel_fnames, addable_rel_fnames, commands)
            self.assertEqual(result, "test input")
            mock_input.assert_called_once()

    @patch("builtins.input")
    def test_confirm_ask_explicit_yes_required(self, mock_input):
        io = InputOutput(pretty=False)

        # Test case 1: explicit_yes_required=True, self.yes=True
        io.yes = True
        result = io.confirm_ask("Are you sure?", explicit_yes_required=True)
        self.assertFalse(result)
        mock_input.assert_not_called()

        # Test case 2: explicit_yes_required=True, self.yes=False
        io.yes = False
        result = io.confirm_ask("Are you sure?", explicit_yes_required=True)
        self.assertFalse(result)
        mock_input.assert_not_called()

        # Test case 3: explicit_yes_required=True, user input required
        io.yes = None
        mock_input.return_value = "y"
        result = io.confirm_ask("Are you sure?", explicit_yes_required=True)
        self.assertTrue(result)
        mock_input.assert_called_once()

        # Reset mock_input
        mock_input.reset_mock()

        # Test case 4: explicit_yes_required=False, self.yes=True
        io.yes = True
        result = io.confirm_ask("Are you sure?", explicit_yes_required=False)
        self.assertTrue(result)
        mock_input.assert_not_called()

    @patch("builtins.input")
    def test_confirm_ask_with_group(self, mock_input):
        io = InputOutput(pretty=False)
        group = ConfirmGroup()

        # Test case 1: No group preference, user selects 'All'
        mock_input.return_value = "a"
        result = io.confirm_ask("Are you sure?", group=group)
        self.assertTrue(result)
        self.assertEqual(group.preference, "all")
        mock_input.assert_called_once()
        mock_input.reset_mock()

        # Test case 2: Group preference is 'All', should not prompt
        result = io.confirm_ask("Are you sure?", group=group)
        self.assertTrue(result)
        mock_input.assert_not_called()

        # Test case 3: No group preference, user selects 'Skip all'
        group.preference = None
        mock_input.return_value = "s"
        result = io.confirm_ask("Are you sure?", group=group)
        self.assertFalse(result)
        self.assertEqual(group.preference, "skip")
        mock_input.assert_called_once()
        mock_input.reset_mock()

        # Test case 4: Group preference is 'Skip all', should not prompt
        result = io.confirm_ask("Are you sure?", group=group)
        self.assertFalse(result)
        mock_input.assert_not_called()

        # Test case 5: explicit_yes_required=True, should not offer 'All' option
        group.preference = None
        mock_input.return_value = "y"
        result = io.confirm_ask("Are you sure?", group=group, explicit_yes_required=True)
        self.assertTrue(result)
        self.assertIsNone(group.preference)
        mock_input.assert_called_once()
        self.assertNotIn("(A)ll", mock_input.call_args[0][0])
        mock_input.reset_mock()

    @patch("builtins.input")
    def test_confirm_ask_yes_no(self, mock_input):
        io = InputOutput(pretty=False)

        # Test case 1: User selects 'Yes'
        mock_input.return_value = "y"
        result = io.confirm_ask("Are you sure?")
        self.assertTrue(result)
        mock_input.assert_called_once()
        mock_input.reset_mock()

        # Test case 2: User selects 'No'
        mock_input.return_value = "n"
        result = io.confirm_ask("Are you sure?")
        self.assertFalse(result)
        mock_input.assert_called_once()
        mock_input.reset_mock()

        # Test case 3: Empty input (default to Yes)
        mock_input.return_value = ""
        result = io.confirm_ask("Are you sure?")
        self.assertTrue(result)
        mock_input.assert_called_once()
        mock_input.reset_mock()

    def test_get_command_completions(self):
        root = ""
        rel_fnames = []
        addable_rel_fnames = []
        commands = MagicMock()
        commands.get_commands.return_value = ["model", "chat", "help"]
        commands.get_completions.return_value = ["gpt-3.5-turbo", "gpt-4"]
        commands.matching_commands.return_value = (["/model", "/models"], None, None)

        autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")

        # Test case for "/model gpt"
        result = autocompleter.get_command_completions("/model gpt", ["/model", "gpt"])
        self.assertEqual(result, ["gpt-3.5-turbo", "gpt-4"])
        commands.get_completions.assert_called_once_with("/model")
        commands.matching_commands.assert_called_once_with("/model")


if __name__ == "__main__":
    unittest.main()
