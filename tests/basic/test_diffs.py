import unittest

from aider.diffs import (
    assert_newlines,
    create_progress_bar,
    diff_partial_update,
    find_last_non_deleted,
)


class TestCreateProgressBar(unittest.TestCase):
    def test_zero_percent(self):
        bar = create_progress_bar(0)
        self.assertEqual(bar, "░" * 30)

    def test_hundred_percent(self):
        bar = create_progress_bar(100)
        self.assertEqual(bar, "█" * 30)

    def test_fifty_percent(self):
        bar = create_progress_bar(50)
        self.assertEqual(bar, "█" * 15 + "░" * 15)

    def test_one_third(self):
        bar = create_progress_bar(33)
        filled = int(30 * 33 // 100)
        self.assertEqual(bar, "█" * filled + "░" * (30 - filled))


class TestAssertNewlines(unittest.TestCase):
    def test_empty_list(self):
        # Should not raise
        assert_newlines([])

    def test_valid_lines(self):
        assert_newlines(["hello\n", "world\n"])

    def test_single_line_no_newline_ok(self):
        # Last line is allowed to lack a newline
        assert_newlines(["hello"])

    def test_missing_newline_in_middle_raises(self):
        with self.assertRaises(AssertionError):
            assert_newlines(["hello", "world\n"])

    def test_empty_string_in_middle_raises(self):
        with self.assertRaises(AssertionError):
            assert_newlines(["", "world\n"])


class TestFindLastNonDeleted(unittest.TestCase):
    def test_identical_content(self):
        lines = ["line1\n", "line2\n", "line3\n"]
        result = find_last_non_deleted(lines, lines[:])
        self.assertEqual(result, 3)

    def test_partial_update(self):
        orig = ["line1\n", "line2\n", "line3\n", "line4\n"]
        updated = ["line1\n", "line2\n"]
        result = find_last_non_deleted(orig, updated)
        self.assertEqual(result, 2)

    def test_updated_with_changes(self):
        orig = ["aaa\n", "bbb\n", "ccc\n"]
        updated = ["aaa\n", "XXX\n"]
        result = find_last_non_deleted(orig, updated)
        # "aaa" matches at position 1, "bbb" is deleted, "XXX" is added
        self.assertEqual(result, 1)

    def test_no_common_lines(self):
        orig = ["aaa\n", "bbb\n"]
        updated = ["xxx\n", "yyy\n"]
        result = find_last_non_deleted(orig, updated)
        self.assertIsNone(result)

    def test_empty_updated(self):
        orig = ["aaa\n", "bbb\n"]
        result = find_last_non_deleted(orig, [])
        self.assertIsNone(result)

    def test_empty_orig(self):
        result = find_last_non_deleted([], ["aaa\n"])
        self.assertIsNone(result)

    def test_both_empty(self):
        result = find_last_non_deleted([], [])
        self.assertIsNone(result)


class TestDiffPartialUpdate(unittest.TestCase):
    def test_returns_empty_when_no_common_lines(self):
        orig = ["aaa\n", "bbb\n"]
        updated = ["xxx\n"]
        result = diff_partial_update(orig, updated)
        self.assertEqual(result, "")

    def test_partial_update_shows_diff_block(self):
        orig = ["line1\n", "line2\n", "line3\n", "line4\n"]
        # Include enough common lines so the diff has visible changes
        updated = ["line1\n", "line2\n", "CHANGED\n"]
        result = diff_partial_update(orig, updated)
        self.assertIn("```diff", result)
        # In non-final mode, the last updated line is replaced with a progress bar
        # The progress bar line should be present
        self.assertIn("lines", result)
        self.assertIn("line1\n", result)

    def test_final_mode_uses_full_orig(self):
        orig = ["line1\n", "line2\n", "line3\n"]
        updated = ["line1\n", "REPLACED\n", "line3\n"]
        result = diff_partial_update(orig, updated, final=True)
        self.assertIn("```diff", result)
        self.assertIn("-line2\n", result)
        self.assertIn("+REPLACED\n", result)
        # In final mode there is no progress bar line replacing the last updated line
        self.assertNotIn("lines [", result)

    def test_fname_appears_in_header(self):
        orig = ["old\n"]
        updated = ["new\n"]
        result = diff_partial_update(orig, updated, final=True, fname="test.py")
        self.assertIn("--- test.py original", result)
        self.assertIn("+++ test.py updated", result)

    def test_no_fname_omits_header(self):
        orig = ["old\n"]
        updated = ["new\n"]
        result = diff_partial_update(orig, updated, final=True)
        self.assertNotIn("---", result)
        self.assertNotIn("+++", result)

    def test_identical_content_final(self):
        lines = ["same\n"]
        result = diff_partial_update(lines, lines[:], final=True)
        # No actual changes, but the function still wraps in backticks
        self.assertIn("```diff", result)

    def test_new_file_empty_orig(self):
        orig = []
        updated = ["new line\n"]
        result = diff_partial_update(orig, updated, final=True)
        self.assertIn("```diff", result)
        self.assertIn("+new line\n", result)

    def test_file_deletion_empty_updated(self):
        orig = ["content\n"]
        updated = []
        result = diff_partial_update(orig, updated, final=True)
        self.assertIn("```diff", result)
        self.assertIn("-content\n", result)

    def test_backtick_escaping(self):
        # If the diff itself contains triple backticks, more backticks should be used
        orig = ["```\n"]
        updated = ["````\n"]
        result = diff_partial_update(orig, updated, final=True)
        # The wrapping fence must use enough backticks to not collide
        lines = result.strip().split("\n")
        opening_fence = lines[0]
        self.assertTrue(len(opening_fence.replace("diff", "")) >= 4)

    def test_progress_bar_percentage_in_partial(self):
        orig = ["l1\n", "l2\n", "l3\n", "l4\n"]
        updated = ["l1\n", "l2\n"]
        result = diff_partial_update(orig, updated)
        # 2 out of 4 lines = 50%
        self.assertIn("50%", result)

    def test_output_ends_with_newline(self):
        orig = ["a\n", "b\n"]
        updated = ["a\n", "c\n"]
        result = diff_partial_update(orig, updated, final=True)
        self.assertTrue(result.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
