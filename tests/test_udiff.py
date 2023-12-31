import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from aider.coders.udiff_coder import UnifiedDiffCoder, do_replace, apply_hunk, find_diffs
from aider.io import InputOutput

class TestUnifiedDiffCoder(unittest.TestCase):
    def setUp(self):
        self.coder = UnifiedDiffCoder(io=InputOutput())

    def test_do_replace_new_file(self):
        # Test do_replace when it should create a new file
        hunk = [
            "--- /dev/null",
            "+++ newfile.txt",
            "@@ -0,0 +1 @@",
            "+New content\n"
        ]
        result = do_replace('newfile.txt', None, hunk)
        self.assertEqual(result, 'New content\n')

    def test_apply_hunk_with_changes(self):
        # Test apply_hunk with actual changes
        content = "Original line 1\nOriginal line 2\n"
        hunk = [
            "@@ -1,2 +1,2 @@",
            " Original line 1",
            "-Original line 2",
            "+Modified line 2"
        ]
        result = apply_hunk(content, hunk)
        self.assertEqual(result, "Original line 1\nModified line 2\n")

    def test_find_diffs_single_hunk(self):
        # Test find_diffs with a single hunk
        content = "```diff\n--- a/file.txt\n+++ b/file.txt\n@@ -1,2 +1,2 @@\n-Original\n+Modified\n```\n"
        result = find_diffs(content)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 'b/file.txt')
        self.assertEqual(result[0][1], ['@@ -1,2 +1,2 @@\n', '-Original\n', '+Modified\n'])

if __name__ == '__main__':
    unittest.main()
