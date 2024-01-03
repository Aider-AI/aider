import unittest

from aider.coders.udiff_coder import find_diffs
from aider.dump import dump  # noqa: F401


class TestUnifiedDiffCoder(unittest.TestCase):
    def test_find_diffs_single_hunk(self):
        # Test find_diffs with a single hunk
        content = """
Some text...

```diff
--- file.txt
+++ file.txt
@@ ... @@
-Original
+Modified
```
"""
        edits = find_diffs(content)
        dump(edits)
        self.assertEqual(len(edits), 1)

        edit = edits[0]
        self.assertEqual(edit[0], "file.txt")
        self.assertEqual(edit[1], ["-Original\n", "+Modified\n"])

    def test_find_diffs_dev_null(self):
        # Test find_diffs with a single hunk
        content = """
Some text...

```diff
--- /dev/null
+++ file.txt
@@ ... @@
-Original
+Modified
```
"""
        edits = find_diffs(content)
        dump(edits)
        self.assertEqual(len(edits), 1)

        edit = edits[0]
        self.assertEqual(edit[0], "file.txt")
        self.assertEqual(edit[1], ["-Original\n", "+Modified\n"])

    def test_find_diffs_dirname_with_spaces(self):
        # Test find_diffs with a single hunk
        content = """
Some text...

```diff
--- dir name with spaces/file.txt
+++ dir name with spaces/file.txt
@@ ... @@
-Original
+Modified
```
"""
        edits = find_diffs(content)
        dump(edits)
        self.assertEqual(len(edits), 1)

        edit = edits[0]
        self.assertEqual(edit[0], "dir name with spaces/file.txt")
        self.assertEqual(edit[1], ["-Original\n", "+Modified\n"])


if __name__ == "__main__":
    unittest.main()
