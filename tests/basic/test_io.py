import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from aider.dump import dump  # noqa: F401
from aider.io import AutoCompleter, ConfirmGroup, InputOutput
from aider.utils import ChdirTemporaryDirectory


class TestInputOutput(unittest.TestCase):
    def test_line_endings_validation(self):
        # Test valid line endings
        for ending in ["platform", "lf", "crlf"]:
            io = InputOutput(line_endings=ending)
            self.assertEqual(
                io.newline, None if ending == "platform" else "\n" if ending == "lf" else "\r\n"
            )

        # Test invalid line endings
        with self.assertRaises(ValueError) as cm:
            io = InputOutput(line_endings="invalid")
        self.assertIn("Invalid line_endings value: invalid", str(cm.exception))
        # Check each valid option is in the error message
        self.assertIn("platform", str(cm.exception))
        self.assertIn("crlf", str(cm.exception))
        self.assertIn("lf", str(cm.exception))

    def test_no_color_environment_variable(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            io = InputOutput(fancy_input=False)
            self.assertFalse(io.pretty)

    def test_color_initialization(self):
        """Test that color values are properly initialized with # prefix"""
        # Test with hex colors without #
        io = InputOutput(
            user_input_color="00cc00",
            tool_error_color="FF2222",
            tool_warning_color="FFA500",
            assistant_output_color="0088ff",
            pretty=True,
        )

        # Check that # was added to hex colors
        self.assertEqual(io.user_input_color, "#00cc00")
        self.assertEqual(io.tool_error_color, "#FF2222")
        self.assertEqual(io.tool_warning_color, "#FFA500")  # Already had #
        self.assertEqual(io.assistant_output_color, "#0088ff")

        # Test with named colors (should be unchanged)
        io = InputOutput(user_input_color="blue", tool_error_color="red", pretty=True)

        self.assertEqual(io.user_input_color, "blue")
        self.assertEqual(io.tool_error_color, "red")

        # Test with pretty=False (should not modify colors)
        io = InputOutput(user_input_color="00cc00", tool_error_color="FF2222", pretty=False)

        self.assertIsNone(io.user_input_color)
        self.assertIsNone(io.tool_error_color)

    def test_dumb_terminal(self):
        with patch.dict(os.environ, {"TERM": "dumb"}):
            io = InputOutput(fancy_input=True)
            self.assertTrue(io.is_dumb_terminal)
            self.assertFalse(io.pretty)
            self.assertIsNone(io.prompt_session)

    def test_autocompleter_get_command_completions(self):
        # Step 3: Mock the commands object
        commands = MagicMock()
        commands.get_commands.return_value = ["/help", "/add", "/drop"]
        commands.matching_commands.side_effect = lambda inp: (
            [cmd for cmd in commands.get_commands() if cmd.startswith(inp.strip().split()[0])],
            inp.strip().split()[0],
            " ".join(inp.strip().split()[1:]),
        )
        commands.get_raw_completions.return_value = None
        commands.get_completions.side_effect = lambda cmd: (
            ["file1.txt", "file2.txt"] if cmd == "/add" else None
        )

        # Step 4: Create an instance of AutoCompleter
        root = ""
        rel_fnames = []
        addable_rel_fnames = []
        autocompleter = AutoCompleter(
            root=root,
            rel_fnames=rel_fnames,
            addable_rel_fnames=addable_rel_fnames,
            commands=commands,
            encoding="utf-8",
        )

        # Step 5: Set up test cases
        test_cases = [
            # Input text, Expected completion texts
            ("/", ["/help", "/add", "/drop"]),
            ("/a", ["/add"]),
            ("/add f", ["file1.txt", "file2.txt"]),
        ]

        # Step 6: Iterate through test cases
        for text, expected_completions in test_cases:
            document = Document(text=text)
            complete_event = CompleteEvent()
            words = text.strip().split()

            # Call get_command_completions
            completions = list(
                autocompleter.get_command_completions(
                    document,
                    complete_event,
                    text,
                    words,
                )
            )

            # Extract completion texts
            completion_texts = [comp.text for comp in completions]

            # Assert that the completions match expected results
            self.assertEqual(set(completion_texts), set(expected_completions))

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
        io = InputOutput(pretty=False, fancy_input=False)  # Windows tests throw UnicodeDecodeError
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
        io = InputOutput(pretty=False, fancy_input=False)

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
        io = InputOutput(pretty=False, fancy_input=False)
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
        io = InputOutput(pretty=False, fancy_input=False)

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

        # Test case 4: 'skip' functions as 'no' without group
        mock_input.return_value = "s"
        result = io.confirm_ask("Are you sure?")
        self.assertFalse(result)
        mock_input.assert_called_once()
        mock_input.reset_mock()

        # Test case 5: 'all' functions as 'yes' without group
        mock_input.return_value = "a"
        result = io.confirm_ask("Are you sure?")
        self.assertTrue(result)
        mock_input.assert_called_once()
        mock_input.reset_mock()

        # Test case 6: Full word 'skip' functions as 'no' without group
        mock_input.return_value = "skip"
        result = io.confirm_ask("Are you sure?")
        self.assertFalse(result)
        mock_input.assert_called_once()
        mock_input.reset_mock()

        # Test case 7: Full word 'all' functions as 'yes' without group
        mock_input.return_value = "all"
        result = io.confirm_ask("Are you sure?")
        self.assertTrue(result)
        mock_input.assert_called_once()
        mock_input.reset_mock()

    @patch("builtins.input", side_effect=["d"])
    def test_confirm_ask_allow_never(self, mock_input):
        """Test the 'don't ask again' functionality in confirm_ask"""
        io = InputOutput(pretty=False, fancy_input=False)

        # First call: user selects "Don't ask again"
        result = io.confirm_ask("Are you sure?", allow_never=True)
        self.assertFalse(result)
        mock_input.assert_called_once()
        self.assertIn(("Are you sure?", None), io.never_prompts)

        # Reset the mock to check for further calls
        mock_input.reset_mock()

        # Second call: should not prompt, immediately return False
        result = io.confirm_ask("Are you sure?", allow_never=True)
        self.assertFalse(result)
        mock_input.assert_not_called()

        # Test with subject parameter
        mock_input.reset_mock()
        mock_input.side_effect = ["d"]
        result = io.confirm_ask("Confirm action?", subject="Subject Text", allow_never=True)
        self.assertFalse(result)
        mock_input.assert_called_once()
        self.assertIn(("Confirm action?", "Subject Text"), io.never_prompts)

        # Subsequent call with the same question and subject
        mock_input.reset_mock()
        result = io.confirm_ask("Confirm action?", subject="Subject Text", allow_never=True)
        self.assertFalse(result)
        mock_input.assert_not_called()

        # Test that allow_never=False does not add to never_prompts
        mock_input.reset_mock()
        mock_input.side_effect = ["d", "n"]
        result = io.confirm_ask("Do you want to proceed?", allow_never=False)
        self.assertFalse(result)
        self.assertEqual(mock_input.call_count, 2)
        self.assertNotIn(("Do you want to proceed?", None), io.never_prompts)


class TestInputOutputMultilineMode(unittest.TestCase):
    def setUp(self):
        self.io = InputOutput(fancy_input=True)
        self.io.prompt_session = MagicMock()

    def test_toggle_multiline_mode(self):
        """Test that toggling multiline mode works correctly"""
        # Start in single-line mode
        self.io.multiline_mode = False

        # Toggle to multiline mode
        self.io.toggle_multiline_mode()
        self.assertTrue(self.io.multiline_mode)

        # Toggle back to single-line mode
        self.io.toggle_multiline_mode()
        self.assertFalse(self.io.multiline_mode)

    def test_tool_message_unicode_fallback(self):
        """Test that Unicode messages are properly converted to ASCII with replacement"""
        io = InputOutput(pretty=False, fancy_input=False)

        # Create a message with invalid Unicode that can't be encoded in UTF-8
        # Using a surrogate pair that's invalid in UTF-8
        invalid_unicode = "Hello \ud800World"

        # Mock console.print to capture the output
        with patch.object(io.console, "print") as mock_print:
            # First call will raise UnicodeEncodeError
            mock_print.side_effect = [UnicodeEncodeError("utf-8", "", 0, 1, "invalid"), None]

            io._tool_message(invalid_unicode)

            # Verify that the message was converted to ASCII with replacement
            self.assertEqual(mock_print.call_count, 2)
            args, kwargs = mock_print.call_args
            converted_message = args[0]

            # The invalid Unicode should be replaced with '?'
            self.assertEqual(converted_message, "Hello ?World")

    def test_multiline_mode_restored_after_interrupt(self):
        """Test that multiline mode is restored after KeyboardInterrupt"""
        io = InputOutput(fancy_input=True)
        io.prompt_session = MagicMock()

        # Start in multiline mode
        io.multiline_mode = True

        # Mock prompt() to raise KeyboardInterrupt
        io.prompt_session.prompt.side_effect = KeyboardInterrupt

        # Test confirm_ask()
        with self.assertRaises(KeyboardInterrupt):
            io.confirm_ask("Test question?")
        self.assertTrue(io.multiline_mode)  # Should be restored

        # Test prompt_ask()
        with self.assertRaises(KeyboardInterrupt):
            io.prompt_ask("Test prompt?")
        self.assertTrue(io.multiline_mode)  # Should be restored

    def test_multiline_mode_restored_after_normal_exit(self):
        """Test that multiline mode is restored after normal exit"""
        io = InputOutput(fancy_input=True)
        io.prompt_session = MagicMock()

        # Start in multiline mode
        io.multiline_mode = True

        # Mock prompt() to return normally
        io.prompt_session.prompt.return_value = "y"

        # Test confirm_ask()
        io.confirm_ask("Test question?")
        self.assertTrue(io.multiline_mode)  # Should be restored

        # Test prompt_ask()
        io.prompt_ask("Test prompt?")
        self.assertTrue(io.multiline_mode)  # Should be restored

    def test_ensure_hash_prefix(self):
        """Test that ensure_hash_prefix correctly adds # to valid hex colors"""
        from aider.io import ensure_hash_prefix

        # Test valid hex colors without #
        self.assertEqual(ensure_hash_prefix("000"), "#000")
        self.assertEqual(ensure_hash_prefix("fff"), "#fff")
        self.assertEqual(ensure_hash_prefix("F00"), "#F00")
        self.assertEqual(ensure_hash_prefix("123456"), "#123456")
        self.assertEqual(ensure_hash_prefix("abcdef"), "#abcdef")
        self.assertEqual(ensure_hash_prefix("ABCDEF"), "#ABCDEF")

        # Test hex colors that already have #
        self.assertEqual(ensure_hash_prefix("#000"), "#000")
        self.assertEqual(ensure_hash_prefix("#123456"), "#123456")

        # Test invalid inputs (should return unchanged)
        self.assertEqual(ensure_hash_prefix(""), "")
        self.assertEqual(ensure_hash_prefix(None), None)
        self.assertEqual(ensure_hash_prefix("red"), "red")  # Named color
        self.assertEqual(ensure_hash_prefix("12345"), "12345")  # Wrong length
        self.assertEqual(ensure_hash_prefix("1234567"), "1234567")  # Wrong length
        self.assertEqual(ensure_hash_prefix("xyz"), "xyz")  # Invalid hex chars
        self.assertEqual(ensure_hash_prefix("12345g"), "12345g")  # Invalid hex chars


if __name__ == "__main__":
    unittest.main()
