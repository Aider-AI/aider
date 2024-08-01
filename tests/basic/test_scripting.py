import unittest
from unittest.mock import patch

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model


class TestScriptingAPI(unittest.TestCase):
    @patch("aider.coders.base_coder.Coder.send")
    def test_basic_scripting(self, mock_send):
        # Setup
        def mock_send_side_effect(messages, functions=None):
            coder.partial_response_content = "Changes applied successfully."
            coder.partial_response_function_call = None
            return "Changes applied successfully."

        mock_send.side_effect = mock_send_side_effect

        # Test script
        fnames = ["greeting.py"]
        model = Model("gpt-4-turbo")
        coder = Coder.create(main_model=model, fnames=fnames)

        result1 = coder.run("make a script that prints hello world")
        result2 = coder.run("make it say goodbye")

        # Assertions
        self.assertEqual(mock_send.call_count, 2)
        mock_send.assert_any_call(
            [{"role": "user", "content": "make a script that prints hello world"}], functions=None
        )
        mock_send.assert_any_call(
            [{"role": "user", "content": "make it say goodbye"}], functions=None
        )
        self.assertEqual(result1, "Changes applied successfully.")
        self.assertEqual(result2, "Changes applied successfully.")
        self.assertEqual(coder.partial_response_content, "Changes applied successfully.")

    @patch("aider.coders.base_coder.Coder.send")
    def test_scripting_with_io(self, mock_send):
        # Setup
        def mock_send_side_effect(messages, functions=None):
            coder.partial_response_content = "New function added successfully."
            coder.partial_response_function_call = None
            return "New function added successfully."

        mock_send.side_effect = mock_send_side_effect

        # Test script
        fnames = ["greeting.py"]
        model = Model("gpt-4-turbo")
        io = InputOutput(yes=True)
        coder = Coder.create(main_model=model, fnames=fnames, io=io)

        result = coder.run("add a new function")

        # Assertions
        mock_send.assert_called_once_with(
            [{"role": "user", "content": "add a new function"}], functions=None
        )
        self.assertEqual(result, "New function added successfully.")
        self.assertTrue(io.yes)  # Check that 'yes' is set to True
        self.assertEqual(coder.partial_response_content, "New function added successfully.")


if __name__ == "__main__":
    unittest.main()
