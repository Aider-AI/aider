import unittest
from unittest.mock import MagicMock, patch

from aider.dump import dump  # noqa
from aider.coders.base_coder import Coder


class TestFix(unittest.TestCase):
    def setUp(self):
        self.io = MagicMock()
        self.coder = Coder(
            main_model=MagicMock(),
            io=self.io,
            fix_cmds={"python": "black"},
        )

    @patch("aider.coders.base_coder.run_cmd")
    def test_fix_edited_success(self, mock_run):
        mock_run.return_value = (0, "")  # Success, no output
        edited = ["test.py"]
        result = self.coder.fix_edited(edited)
        self.assertEqual(result, "")
        mock_run.assert_called_once_with("black test.py")

    @patch("aider.coders.base_coder.run_cmd")
    def test_fix_edited_error(self, mock_run):
        error_output = "Error: invalid syntax"
        mock_run.return_value = (1, error_output)  # Error with output
        edited = ["test.py"]
        result = self.coder.fix_edited(edited)
        self.assertIn(error_output, result)
        mock_run.assert_called_once_with("black test.py")

    @patch("aider.coders.base_coder.run_cmd")
    def test_fix_edited_no_cmd(self, mock_run):
        self.coder.fix_cmds = {}  # No fix command configured
        edited = ["test.py"]
        result = self.coder.fix_edited(edited)
        self.assertIsNone(result)
        mock_run.assert_not_called()

    @patch("aider.coders.base_coder.run_cmd")
    def test_fix_edited_multiple_files(self, mock_run):
        mock_run.side_effect = [(0, ""), (1, "Error in file2")]
        edited = ["file1.py", "file2.py"]
        result = self.coder.fix_edited(edited)
        self.assertIn("Error in file2", result)
        self.assertEqual(mock_run.call_count, 2)

    @patch("aider.coders.base_coder.run_cmd")
    def test_fix_edited_empty_filename(self, mock_run):
        edited = [""]
        result = self.coder.fix_edited(edited)
        self.assertEqual(result, "")
        mock_run.assert_not_called()

    @patch("aider.coders.base_coder.run_cmd")
    def test_fix_edited_different_language(self, mock_run):
        self.coder.fix_cmds = {"go": "gofmt -w"}
        edited = ["test.py"]  # Python file but only Go formatter configured
        result = self.coder.fix_edited(edited)
        self.assertIsNone(result)
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
