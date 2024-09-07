import unittest
from unittest.mock import MagicMock, patch

from aider.dump import dump  # noqa
from aider.linter import Linter


class TestLinter(unittest.TestCase):
    def setUp(self):
        self.linter = Linter(encoding="utf-8", root="/test/root")

    def test_init(self):
        self.assertEqual(self.linter.encoding, "utf-8")
        self.assertEqual(self.linter.root, "/test/root")
        self.assertIn("python", self.linter.languages)

    def test_set_linter(self):
        self.linter.set_linter("javascript", "eslint")
        self.assertEqual(self.linter.languages["javascript"], "eslint")

    def test_get_rel_fname(self):
        import os

        self.assertEqual(self.linter.get_rel_fname("/test/root/file.py"), "file.py")
        expected_path = os.path.normpath("../../other/path/file.py")
        actual_path = os.path.normpath(self.linter.get_rel_fname("/other/path/file.py"))
        self.assertEqual(actual_path, expected_path)

    @patch("subprocess.Popen")
    def test_run_cmd(self, mock_popen):
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("", None)
        mock_popen.return_value = mock_process

        result = self.linter.run_cmd("test_cmd", "test_file.py", "code")
        self.assertIsNone(result)

    @patch("subprocess.Popen")
    def test_run_cmd_with_errors(self, mock_popen):
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("Error message", None)
        mock_popen.return_value = mock_process

        result = self.linter.run_cmd("test_cmd", "test_file.py", "code")
        self.assertIsNotNone(result)
        self.assertIn("Error message", result.text)


if __name__ == "__main__":
    unittest.main()
