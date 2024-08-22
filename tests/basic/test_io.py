import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aider.io import AutoCompleter, InputOutput
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
            self.assertEqual(autocompleter.words, set(rel_fnames + ["hello"]))

            encoding = "utf-16"
            some_content_which_will_error_if_read_with_encoding_utf8 = "ÅÍÎÏ".encode(encoding)
            with open(fname, "wb") as f:
                f.write(some_content_which_will_error_if_read_with_encoding_utf8)

            autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")
            self.assertEqual(autocompleter.words, set(rel_fnames))

    @patch("aider.io.PromptSession")
    def test_get_input_is_a_directory_error(self, MockPromptSession):
        # Mock the PromptSession to simulate user input
        mock_session = MockPromptSession.return_value
        mock_session.prompt.return_value = "test input"

        io = InputOutput(pretty=False)  # Windows tests throw UnicodeDecodeError
        root = "/"
        rel_fnames = ["existing_file.txt"]
        addable_rel_fnames = ["new_file.txt"]
        commands = MagicMock()

        # Simulate IsADirectoryError
        with patch("aider.io.open", side_effect=IsADirectoryError):
            result = io.get_input(root, rel_fnames, addable_rel_fnames, commands)
            self.assertEqual(result, "test input")

    @patch('aider.io.prompt')
    def test_confirm_ask_explicit_yes_required(self, mock_prompt):
        io = InputOutput(pretty=False)

        # Test case 1: explicit_yes_required=True, self.yes=True
        io.yes = True
        result = io.confirm_ask("Are you sure?", explicit_yes_required=True)
        self.assertFalse(result)
        mock_prompt.assert_not_called()

        # Test case 2: explicit_yes_required=True, self.yes=False
        io.yes = False
        result = io.confirm_ask("Are you sure?", explicit_yes_required=True)
        self.assertFalse(result)
        mock_prompt.assert_not_called()

        # Test case 3: explicit_yes_required=True, user input required
        io.yes = None
        mock_prompt.return_value = 'y'
        result = io.confirm_ask("Are you sure?", explicit_yes_required=True)
        self.assertTrue(result)
        mock_prompt.assert_called_once()

        # Reset mock_prompt
        mock_prompt.reset_mock()

        # Test case 4: explicit_yes_required=False, self.yes=True
        io.yes = True
        result = io.confirm_ask("Are you sure?", explicit_yes_required=False)
        self.assertTrue(result)
        mock_prompt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
