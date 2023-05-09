import unittest
from utils import replace_most_similar_chunk

class TestUtils(unittest.TestCase):
    def test_replace_most_similar_chunk(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line."
        part = "This is a sample text"
        replace = "This is a replaced text."
        expected_output = "This is a replaced text.\nAnother line of text.\nYet another line."

        result = replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_replace_most_similar_chunk_not_perfect_match(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line."
        part = "This was a sample text.\nAnother line of txt"
        replace = "This is a replaced text.\nModified line of text."
        expected_output = "This is a replaced text.\nModified line of text.\nYet another line."

        result = replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping(self):
        input_text = "filename.ext\n```\nWe just want this content\nNot the filename and triple quotes\n```"
        expected_output = "We just want this content\nNot the filename and triple quotes\n"
        result = strip_quoted_wrapping(input_text, "filename.ext")
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping_no_filename(self):
        input_text = "```\nWe just want this content\nNot the triple quotes\n```"
        expected_output = "We just want this content\nNot the triple quotes\n"
        result = strip_quoted_wrapping(input_text)
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping_no_wrapping(self):
        input_text = "We just want this content\nNot the triple quotes\n"
        expected_output = "We just want this content\nNot the triple quotes\n"
        result = strip_quoted_wrapping(input_text)
        self.assertEqual(result, expected_output)

if __name__ == "__main__":
    unittest.main()