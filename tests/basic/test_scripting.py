import unittest
from unittest.mock import MagicMock, patch

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model


class TestScriptingAPI(unittest.TestCase):
    @patch("aider.coders.Coder.create")
    @patch("aider.models.Model")
    def test_basic_scripting(self, mock_model, mock_coder_create):
        # Setup
        mock_coder = MagicMock()
        mock_coder_create.return_value = mock_coder

        # Test script
        fnames = ["greeting.py"]
        model = Model("gpt-4-turbo")
        coder = Coder.create(main_model=model, fnames=fnames)

        coder.run("make a script that prints hello world")
        coder.run("make it say goodbye")

        # Assertions
        mock_model.assert_called_once_with("gpt-4-turbo")
        mock_coder_create.assert_called_once_with(main_model=model, fnames=fnames)
        self.assertEqual(mock_coder.run.call_count, 2)
        mock_coder.run.assert_any_call("make a script that prints hello world")
        mock_coder.run.assert_any_call("make it say goodbye")

    @patch("aider.coders.Coder.create")
    @patch("aider.models.Model")
    def test_scripting_with_io(self, mock_model, mock_coder_create):
        # Setup
        mock_coder = MagicMock()
        mock_coder_create.return_value = mock_coder

        # Test script
        fnames = ["greeting.py"]
        model = Model("gpt-4-turbo")
        io = InputOutput(yes=True)
        coder = Coder.create(main_model=model, fnames=fnames, io=io)

        coder.run("add a new function")

        # Assertions
        mock_model.assert_called_once_with("gpt-4-turbo")
        mock_coder_create.assert_called_once_with(main_model=model, fnames=fnames, io=io)
        mock_coder.run.assert_called_once_with("add a new function")
        self.assertTrue(io.yes)  # Check that 'yes' is set to True


if __name__ == "__main__":
    unittest.main()
