import unittest
from unittest.mock import MagicMock, patch

from aider.linter import Linter


class TestLinter(unittest.TestCase):
    def setUp(self):
        self.linter = Linter(encoding="utf-8", root="/test/root")

    def test_init(self):
        self.assertEqual(self.linter.encoding, "utf-8")
        self.assertEqual(self.linter.root, "/test/root")
        self.assertIn("python", self.linter.languages)

    @patch("pathlib.Path.is_file")
    def test_check_eslint_unix(self, mock_is_file):
        mock_is_file.return_value = True
        self.linter._check_eslint()
        self.assertIn("typescript", self.linter.languages)
        self.assertTrue(self.linter.languages["typescript"].startswith('"'))
        self.assertTrue(self.linter.languages["typescript"].endswith('" --format unix'))

    @patch("pathlib.Path.is_file")
    def test_check_eslint_windows(self, mock_is_file):
        def side_effect(path):
            return str(path).endswith("eslint.cmd")

        mock_is_file.side_effect = side_effect
        self.linter._check_eslint()
        self.assertIn("typescript", self.linter.languages)
        self.assertTrue(self.linter.languages["typescript"].endswith('eslint.cmd" --format unix'))

    def test_set_linter(self):
        self.linter.set_linter("javascript", "eslint")
        self.assertEqual(self.linter.languages["javascript"], "eslint")

    def test_get_rel_fname(self):
        self.assertEqual(self.linter.get_rel_fname("/test/root/file.py"), "file.py")
        self.assertEqual(self.linter.get_rel_fname("/other/path/file.py"), "/other/path/file.py")

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
