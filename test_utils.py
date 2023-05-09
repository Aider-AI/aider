import unittest
from utils import replace_most_similar_chunk

class TestUtils(unittest.TestCase):
    def test_replace_most_similar_chunk(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line."
        part = "sample text"
        replace = "replaced text"
        expected_output = "This is a replaced text.\nAnother line of text.\nYet another line."

        result = replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_replace_most_similar_chunk_not_perfect_match(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line."
        part = "sample text.\nAnother line"
        replace = "replaced text.\nModified line"
        expected_output = "This is a replaced text.\nModified line of text.\nYet another line."

        result = replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

if __name__ == "__main__":
    unittest.main()