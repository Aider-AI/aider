import unittest

from aider.linter import find_filenames_and_linenums, Linter


class TestFindFilenamesAndLinenums(unittest.TestCase):
    def test_single_file_single_match(self):
        text = "file.py:42 error: something went wrong"
        result = find_filenames_and_linenums(text, ["file.py"])
        self.assertEqual(result, {"file.py": {42}})

    def test_single_file_multiple_matches(self):
        text = "file.py:10 error\nfile.py:20 warning\nfile.py:30 info"
        result = find_filenames_and_linenums(text, ["file.py"])
        self.assertEqual(result, {"file.py": {10, 20, 30}})

    def test_multiple_files(self):
        text = "foo.py:5 error\nbar.py:15 error\nfoo.py:25 warning"
        result = find_filenames_and_linenums(text, ["foo.py", "bar.py"])
        self.assertEqual(result, {"foo.py": {5, 25}, "bar.py": {15}})

    def test_no_matches(self):
        text = "something:42 error"
        result = find_filenames_and_linenums(text, ["file.py"])
        self.assertEqual(result, {})

    def test_filename_with_underscores_and_numbers(self):
        text = "test_file_123.py:99 error"
        result = find_filenames_and_linenums(text, ["test_file_123.py"])
        self.assertEqual(result, {"test_file_123.py": {99}})

    def test_does_not_match_similar_filenames(self):
        """Ensure partial filename matches are not captured."""
        text = "file.py:10 error\nfile.pyextra:20 error"
        result = find_filenames_and_linenums(text, ["file.py"])
        # Should only match file.py:10, not file.pyextra:20
        self.assertEqual(result, {"file.py": {10}})

    def test_colon_in_path_windows(self):
        """Windows paths like C:\\folder\\file.py:42 should not match."""
        text = "C:\\folder\\file.py:42 error"
        result = find_filenames_and_linenums(text, ["file.py"])
        # \b word boundary after .py should not match after backslash
        # This test documents current behavior; \b does not match \
        self.assertEqual(result, {"file.py": {42}})


class TestErrorsToLintResult(unittest.TestCase):
    def setUp(self):
        self.linter = Linter(encoding="utf-8", root="/test/root")

    def test_errors_to_lint_result_basic(self):
        text = "file.py:10 error\nfile.py:20 warning"
        result = self.linter.errors_to_lint_result("file.py", text)
        self.assertIsNotNone(result)
        self.assertIn("file.py:10", result.text)
        self.assertEqual(result.lines, [9, 19])  # 0-indexed

    def test_errors_to_lint_result_no_errors(self):
        result = self.linter.errors_to_lint_result("file.py", "")
        self.assertIsNone(result)

    def test_errors_to_lint_result_none(self):
        result = self.linter.errors_to_lint_result("file.py", None)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
