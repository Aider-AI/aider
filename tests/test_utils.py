# flake8: noqa: E501

import unittest

from aider import utils


class TestUtils(unittest.TestCase):
    def test_replace_most_similar_chunk(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line.\n"
        part = "This is a sample text"
        replace = "This is a replaced text."
        expected_output = "This is a replaced text..\nAnother line of text.\nYet another line.\n"

        result = utils.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_replace_most_similar_chunk_not_perfect_match(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line."
        part = "This was a sample text.\nAnother line of txt"
        replace = "This is a replaced text.\nModified line of text."
        expected_output = "This is a replaced text.\nModified line of text.\nYet another line."

        result = utils.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping(self):
        input_text = (
            "filename.ext\n```\nWe just want this content\nNot the filename and triple quotes\n```"
        )
        expected_output = "We just want this content\nNot the filename and triple quotes\n"
        result = utils.strip_quoted_wrapping(input_text, "filename.ext")
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping_no_filename(self):
        input_text = "```\nWe just want this content\nNot the triple quotes\n```"
        expected_output = "We just want this content\nNot the triple quotes\n"
        result = utils.strip_quoted_wrapping(input_text)
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping_no_wrapping(self):
        input_text = "We just want this content\nNot the triple quotes\n"
        expected_output = "We just want this content\nNot the triple quotes\n"
        result = utils.strip_quoted_wrapping(input_text)
        self.assertEqual(result, expected_output)

    def test_find_original_update_blocks(self):
        edit = """
Here's the change:

```text
foo.txt
<<<<<<< ORIGINAL
Two
=======
Tooooo
>>>>>>> UPDATED
```

Hope you like it!
"""

        edits = list(utils.find_original_update_blocks(edit))
        self.assertEqual(edits, [("foo.txt", "Two\n", "Tooooo\n")])

    def test_find_original_update_blocks_quote_below_filename(self):
        edit = """
Here's the change:

foo.txt
```text
<<<<<<< ORIGINAL
Two
=======
Tooooo
>>>>>>> UPDATED
```

Hope you like it!
"""

        edits = list(utils.find_original_update_blocks(edit))
        self.assertEqual(edits, [("foo.txt", "Two\n", "Tooooo\n")])

    def test_find_original_update_blocks_unclosed(self):
        edit = """
Here's the change:

```text
foo.txt
<<<<<<< ORIGINAL
Two
=======
Tooooo


oops!
"""

        with self.assertRaises(ValueError) as cm:
            list(utils.find_original_update_blocks(edit))
        self.assertIn("Incomplete", str(cm.exception))

    def test_find_original_update_blocks_missing_filename(self):
        edit = """
Here's the change:

```text
<<<<<<< ORIGINAL
Two
=======
Tooooo


oops!
"""

        with self.assertRaises(ValueError) as cm:
            list(utils.find_original_update_blocks(edit))
        self.assertIn("filename", str(cm.exception))

    def test_find_original_update_blocks_no_final_newline(self):
        edit = """
aider/coder.py
<<<<<<< ORIGINAL
            self.console.print("[red]^C again to quit")
=======
            self.io.tool_error("^C again to quit")
>>>>>>> UPDATED

aider/coder.py
<<<<<<< ORIGINAL
            self.io.tool_error("Malformed ORIGINAL/UPDATE blocks, retrying...")
            self.io.tool_error(err)
=======
            self.io.tool_error("Malformed ORIGINAL/UPDATE blocks, retrying...")
            self.io.tool_error(str(err))
>>>>>>> UPDATED

aider/coder.py
<<<<<<< ORIGINAL
            self.console.print("[red]Unable to get commit message from gpt-3.5-turbo. Use /commit to try again.\n")
=======
            self.io.tool_error("Unable to get commit message from gpt-3.5-turbo. Use /commit to try again.")
>>>>>>> UPDATED

aider/coder.py
<<<<<<< ORIGINAL
            self.console.print("[red]Skipped commmit.")
=======
            self.io.tool_error("Skipped commmit.")
>>>>>>> UPDATED"""

        # Should not raise a ValueError
        list(utils.find_original_update_blocks(edit))


if __name__ == "__main__":
    unittest.main()
