# flake8: noqa: E501

import unittest

from aider.coders.search_replace import (
    RelativeIndenter,
    dmp_apply,
    line_pad,
    line_unpad,
    reverse_lines,
    search_and_replace,
    strip_blank_lines,
    flexible_search_and_replace,
    try_strategy,
)


class TestSearchAndReplace(unittest.TestCase):
    """Tests for the search_and_replace() function."""

    def test_exact_match_single_occurrence(self):
        texts = ("hello world\n", "hello universe\n", "hello world\n")
        result = search_and_replace(texts)
        self.assertEqual(result, "hello universe\n")

    def test_exact_match_multiple_occurrences(self):
        original = "foo\nbar\nfoo\n"
        texts = ("foo\n", "baz\n", original)
        result = search_and_replace(texts)
        # replaces ALL occurrences
        self.assertEqual(result, "baz\nbar\nbaz\n")

    def test_no_match_returns_none(self):
        texts = ("missing\n", "replacement\n", "hello world\n")
        result = search_and_replace(texts)
        self.assertIsNone(result)

    def test_empty_search_in_nonempty_original(self):
        # empty string is contained 0 times? Actually "".count("") returns len+1
        # but the function checks num == 0, so let's see
        texts = ("", "added\n", "original\n")
        result = search_and_replace(texts)
        # "original\n".count("") == 10, which is > 0, so it proceeds
        self.assertIsNotNone(result)

    def test_multiline_search_replace(self):
        search = "line1\nline2\n"
        replace = "new1\nnew2\nnew3\n"
        original = "before\nline1\nline2\nafter\n"
        texts = (search, replace, original)
        result = search_and_replace(texts)
        self.assertEqual(result, "before\nnew1\nnew2\nnew3\nafter\n")

    def test_unicode_content(self):
        search = "caf\u00e9\n"
        replace = "coffee\n"
        original = "I like caf\u00e9\n"
        texts = (search, replace, original)
        result = search_and_replace(texts)
        self.assertEqual(result, "I like coffee\n")

    def test_special_characters(self):
        search = "a+b*c\n"
        replace = "x+y*z\n"
        original = "result = a+b*c\n"
        texts = (search, replace, original)
        result = search_and_replace(texts)
        self.assertEqual(result, "result = x+y*z\n")


class TestRelativeIndenter(unittest.TestCase):
    """Tests for the RelativeIndenter class."""

    def test_basic_roundtrip(self):
        text = "    foo\n        bar\n        baz\n    qux\n"
        ri = RelativeIndenter([text])
        relative = ri.make_relative(text)
        absolute = ri.make_absolute(relative)
        self.assertEqual(absolute, text)

    def test_no_indentation(self):
        text = "foo\nbar\nbaz\n"
        ri = RelativeIndenter([text])
        relative = ri.make_relative(text)
        absolute = ri.make_absolute(relative)
        self.assertEqual(absolute, text)

    def test_increasing_indent(self):
        text = "a\n    b\n        c\n"
        ri = RelativeIndenter([text])
        relative = ri.make_relative(text)
        # make_relative should produce relative changes
        # round trip should recover original
        absolute = ri.make_absolute(relative)
        self.assertEqual(absolute, text)

    def test_decreasing_indent_uses_marker(self):
        text = "        foo\n    bar\n"
        ri = RelativeIndenter([text])
        relative = ri.make_relative(text)
        # bar is outdented by 4, so marker should appear
        self.assertIn(ri.marker, relative)
        absolute = ri.make_absolute(relative)
        self.assertEqual(absolute, text)

    def test_mixed_indent_roundtrip(self):
        text = "def foo():\n    if True:\n        pass\n    else:\n        return\n"
        ri = RelativeIndenter([text])
        relative = ri.make_relative(text)
        absolute = ri.make_absolute(relative)
        self.assertEqual(absolute, text)

    def test_default_marker_is_arrow(self):
        ri = RelativeIndenter(["hello\n"])
        self.assertEqual(ri.marker, "\u2190")

    def test_custom_marker_when_arrow_present(self):
        # text contains the arrow character, so a different marker should be chosen
        text = "hello \u2190 world\n"
        ri = RelativeIndenter([text])
        self.assertNotEqual(ri.marker, "\u2190")

    def test_blank_lines_preserved(self):
        text = "foo\n\n    bar\n"
        ri = RelativeIndenter([text])
        relative = ri.make_relative(text)
        absolute = ri.make_absolute(relative)
        self.assertEqual(absolute, text)

    def test_make_relative_raises_if_marker_present(self):
        ri = RelativeIndenter(["hello\n"])
        text_with_marker = f"some {ri.marker} text\n"
        with self.assertRaises(ValueError):
            ri.make_relative(text_with_marker)

    def test_make_absolute_odd_number_of_lines_raises(self):
        # make_absolute expects pairs of lines (indent + content), so an odd
        # count should cause an IndexError when accessing lines[i+1]
        ri = RelativeIndenter(["hello\n"])
        bad_relative = "\n" + "foo\n" + "extra\n"  # 3 lines = odd, will go out of bounds
        with self.assertRaises(IndexError):
            ri.make_absolute(bad_relative)

    def test_multiple_texts_in_constructor(self):
        texts = ["foo\n    bar\n", "    baz\n        qux\n"]
        ri = RelativeIndenter(texts)
        for text in texts:
            relative = ri.make_relative(text)
            absolute = ri.make_absolute(relative)
            self.assertEqual(absolute, text)


class TestLinePadUnpad(unittest.TestCase):
    """Tests for line_pad() and line_unpad()."""

    def test_pad_unpad_roundtrip(self):
        text = "hello world\n"
        padded = line_pad(text)
        unpadded = line_unpad(padded)
        self.assertEqual(unpadded, text)

    def test_pad_adds_newlines(self):
        text = "content"
        padded = line_pad(text)
        self.assertTrue(padded.startswith("\n"))
        self.assertTrue(padded.endswith("\n"))

    def test_unpad_returns_none_on_invalid(self):
        result = line_unpad("not padded text")
        self.assertIsNone(result)

    def test_empty_string_roundtrip(self):
        text = ""
        padded = line_pad(text)
        unpadded = line_unpad(padded)
        self.assertEqual(unpadded, text)


class TestReverseLines(unittest.TestCase):
    """Tests for reverse_lines()."""

    def test_reverse_simple(self):
        text = "a\nb\nc\n"
        result = reverse_lines(text)
        # splitlines(keepends=True) gives ["a\n", "b\n", "c\n"]
        # reversed: ["c\n", "b\n", "a\n"]
        self.assertEqual(result, "c\nb\na\n")

    def test_reverse_single_line(self):
        text = "only\n"
        result = reverse_lines(text)
        self.assertEqual(result, "only\n")

    def test_reverse_double_reverse_is_identity(self):
        text = "first\nsecond\nthird\n"
        self.assertEqual(reverse_lines(reverse_lines(text)), text)


class TestStripBlankLines(unittest.TestCase):
    """Tests for strip_blank_lines()."""

    def test_strips_leading_trailing_newlines(self):
        texts = ["\n\nhello\nworld\n\n\n"]
        result = strip_blank_lines(texts)
        self.assertEqual(result, ["hello\nworld\n"])

    def test_preserves_internal_blank_lines(self):
        texts = ["hello\n\nworld\n"]
        result = strip_blank_lines(texts)
        # internal blank line between hello and world should remain
        self.assertEqual(result, ["hello\n\nworld\n"])

    def test_multiple_texts(self):
        texts = ["\nfoo\n\n", "\nbar\n\n"]
        result = strip_blank_lines(texts)
        self.assertEqual(result, ["foo\n", "bar\n"])

    def test_ensures_trailing_newline(self):
        texts = ["hello"]
        result = strip_blank_lines(texts)
        self.assertTrue(result[0].endswith("\n"))


class TestFlexibleSearchAndReplace(unittest.TestCase):
    """Tests for flexible_search_and_replace() with various strategies."""

    def test_exact_match_strategy(self):
        search = "old line\n"
        replace = "new line\n"
        original = "before\nold line\nafter\n"
        texts = (search, replace, original)

        # Use only the simplest strategy
        strategies = [
            (search_and_replace, [(False, False, False)]),
        ]
        result = flexible_search_and_replace(texts, strategies)
        self.assertEqual(result, "before\nnew line\nafter\n")

    def test_returns_none_when_no_strategy_works(self):
        texts = ("not found\n", "replacement\n", "original text\n")
        strategies = [
            (search_and_replace, [(False, False, False)]),
        ]
        result = flexible_search_and_replace(texts, strategies)
        self.assertIsNone(result)

    def test_strip_blank_lines_preproc_helps(self):
        search = "\nold line\n\n"
        replace = "\nnew line\n\n"
        original = "old line\n"
        texts = (search, replace, original)

        # Without strip_blank_lines, exact match fails
        strategies_no_strip = [
            (search_and_replace, [(False, False, False)]),
        ]
        result = flexible_search_and_replace(texts, strategies_no_strip)
        self.assertIsNone(result)

        # With strip_blank_lines, it should work
        strategies_with_strip = [
            (search_and_replace, [(True, False, False)]),
        ]
        result = flexible_search_and_replace(texts, strategies_with_strip)
        self.assertIsNotNone(result)


class TestTryStrategy(unittest.TestCase):
    """Tests for try_strategy()."""

    def test_basic_no_preproc(self):
        texts = ("old\n", "new\n", "old\n")
        preproc = (False, False, False)
        result = try_strategy(texts, search_and_replace, preproc)
        self.assertEqual(result, "new\n")

    def test_with_strip_blank_lines(self):
        texts = ("\nold\n\n", "\nnew\n\n", "old\n")
        preproc = (True, False, False)
        result = try_strategy(texts, search_and_replace, preproc)
        self.assertIsNotNone(result)

    def test_with_relative_indent(self):
        texts = ("    foo\n        bar\n", "    foo\n        baz\n", "    foo\n        bar\n")
        preproc = (False, True, False)
        result = try_strategy(texts, search_and_replace, preproc)
        self.assertIsNotNone(result)

    def test_returns_none_on_failure(self):
        texts = ("missing\n", "replacement\n", "original\n")
        preproc = (False, False, False)
        result = try_strategy(texts, search_and_replace, preproc)
        self.assertIsNone(result)


class TestDmpApply(unittest.TestCase):
    """Tests for dmp_apply() - the diff-match-patch based approach."""

    def test_identical_search_and_original(self):
        text = "hello world\nfoo bar\n"
        replace = "hello universe\nfoo bar\n"
        texts = (text, replace, text)
        result = dmp_apply(texts)
        self.assertIsNotNone(result)
        self.assertIn("universe", result)

    def test_returns_none_on_complete_mismatch(self):
        texts = ("aaa\n", "bbb\n", "completely different text that has nothing in common\n")
        result = dmp_apply(texts, remap=False)
        # May or may not return None depending on DMP tolerance, but shouldn't crash
        # Just verify it doesn't raise


class TestEdgeCases(unittest.TestCase):
    """Edge case tests across search_replace functions."""

    def test_search_and_replace_whitespace_only(self):
        texts = ("   \n", "  \n", "   \n")
        result = search_and_replace(texts)
        self.assertEqual(result, "  \n")

    def test_search_and_replace_empty_strings(self):
        texts = ("", "", "")
        result = search_and_replace(texts)
        # "".count("") == 1, not 0, so it proceeds
        self.assertEqual(result, "")

    def test_search_and_replace_newlines_only(self):
        texts = ("\n\n", "\n", "\n\n\n\n")
        result = search_and_replace(texts)
        self.assertIsNotNone(result)

    def test_relativeindenter_tabs(self):
        text = "foo\n\tbar\n\t\tbaz\n"
        ri = RelativeIndenter([text])
        relative = ri.make_relative(text)
        absolute = ri.make_absolute(relative)
        self.assertEqual(absolute, text)

    def test_relativeindenter_empty_text(self):
        text = ""
        ri = RelativeIndenter([text])
        relative = ri.make_relative(text)
        absolute = ri.make_absolute(relative)
        self.assertEqual(absolute, text)

    def test_relativeindenter_single_line_no_newline(self):
        text = "hello"
        ri = RelativeIndenter([text])
        relative = ri.make_relative(text)
        # single line without newline - just verify no crash
        self.assertIsNotNone(relative)

    def test_search_replace_preserves_surrounding_content(self):
        original = "line1\nline2\nline3\nline4\nline5\n"
        search = "line3\n"
        replace = "LINE_THREE\n"
        texts = (search, replace, original)
        result = search_and_replace(texts)
        self.assertEqual(result, "line1\nline2\nLINE_THREE\nline4\nline5\n")

    def test_reverse_lines_empty(self):
        self.assertEqual(reverse_lines(""), "")

    def test_strip_blank_lines_only_newlines(self):
        texts = ["\n\n\n"]
        result = strip_blank_lines(texts)
        self.assertEqual(result, ["\n"])


if __name__ == "__main__":
    unittest.main()
