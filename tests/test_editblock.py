# flake8: noqa: E501

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aider import models
from aider.coders import Coder
from aider.coders import editblock_coder as eb
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("aider.coders.base_coder.check_model_availability")
        self.mock_check = self.patcher.start()
        self.mock_check.return_value = True

    def tearDown(self):
        self.patcher.stop()

    def test_replace_most_similar_chunk(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line.\n"
        part = "This is a sample text"
        replace = "This is a replaced text."
        expected_output = "This is a replaced text..\nAnother line of text.\nYet another line.\n"

        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_replace_most_similar_chunk_not_perfect_match(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line."
        part = "This was a sample text.\nAnother line of txt"
        replace = "This is a replaced text.\nModified line of text."
        expected_output = "This is a replaced text.\nModified line of text.\nYet another line."

        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping(self):
        input_text = (
            "filename.ext\n```\nWe just want this content\nNot the filename and triple quotes\n```"
        )
        expected_output = "We just want this content\nNot the filename and triple quotes\n"
        result = eb.strip_quoted_wrapping(input_text, "filename.ext")
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping_no_filename(self):
        input_text = "```\nWe just want this content\nNot the triple quotes\n```"
        expected_output = "We just want this content\nNot the triple quotes\n"
        result = eb.strip_quoted_wrapping(input_text)
        self.assertEqual(result, expected_output)

    def test_strip_quoted_wrapping_no_wrapping(self):
        input_text = "We just want this content\nNot the triple quotes\n"
        expected_output = "We just want this content\nNot the triple quotes\n"
        result = eb.strip_quoted_wrapping(input_text)
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

        edits = list(eb.find_original_update_blocks(edit))
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

        edits = list(eb.find_original_update_blocks(edit))
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
            list(eb.find_original_update_blocks(edit))
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
            list(eb.find_original_update_blocks(edit))
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
        list(eb.find_original_update_blocks(edit))

    def test_incomplete_edit_block_missing_filename(self):
        edit = """
No problem! Here are the changes to patch `subprocess.check_output` instead of `subprocess.run` in both tests:

```python
tests/test_repomap.py
<<<<<<< ORIGINAL
    def test_check_for_ctags_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("ctags not found")
=======
    def test_check_for_ctags_failure(self):
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = Exception("ctags not found")
>>>>>>> UPDATED

<<<<<<< ORIGINAL
    def test_check_for_ctags_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = CompletedProcess(args=["ctags", "--version"], returncode=0, stdout='''{
  "_type": "tag",
  "name": "status",
  "path": "aider/main.py",
  "pattern": "/^    status = main()$/",
  "kind": "variable"
}''')
=======
    def test_check_for_ctags_success(self):
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.return_value = '''{
  "_type": "tag",
  "name": "status",
  "path": "aider/main.py",
  "pattern": "/^    status = main()$/",
  "kind": "variable"
}'''
>>>>>>> UPDATED
```

These changes replace the `subprocess.run` patches with `subprocess.check_output` patches in both `test_check_for_ctags_failure` and `test_check_for_ctags_success` tests.
"""
        edit_blocks = list(eb.find_original_update_blocks(edit))
        self.assertEqual(len(edit_blocks), 2)  # 2 edits
        self.assertEqual(edit_blocks[0][0], "tests/test_repomap.py")
        self.assertEqual(edit_blocks[1][0], "tests/test_repomap.py")

    def test_replace_part_with_missing_leading_whitespace(self):
        whole = "    line1\n    line2\n    line3\n"
        part = "line1\nline2"
        replace = "new_line1\nnew_line2"
        expected_output = "    new_line1\n    new_line2\n    line3\n"

        result = eb.replace_part_with_missing_leading_whitespace(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_replace_part_with_missing_leading_whitespace_including_blank_lines(self):
        """
        The part has leading whitespace on all lines, so should be ignored.
        But it has a *blank* line with no whitespace at all, which was causing a
        bug per issue #25. Test case to repro and confirm fix.
        """
        whole = "    line1\n    line2\n    line3\n"
        part = "\n  line1\n  line2"
        replace = "new_line1\nnew_line2"
        expected_output = None

        result = eb.replace_part_with_missing_leading_whitespace(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_full_edit(self):
        # Create a few temporary files
        _, file1 = tempfile.mkstemp()

        with open(file1, "w", encoding="utf-8") as f:
            f.write("one\ntwo\nthree\n")

        files = [file1]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(
            models.GPT4, "diff", io=InputOutput(), openai_api_key="fake_key", fnames=files
        )

        def mock_send(*args, **kwargs):
            coder.partial_response_content = f"""
Do this:

{Path(file1).name}
<<<<<<< ORIGINAL
two
=======
new
>>>>>>> UPDATED

"""
            coder.partial_response_function_call = dict()

        coder.send = MagicMock(side_effect=mock_send)

        # Call the run method with a message
        coder.run(with_message="hi")

        content = Path(file1).read_text(encoding="utf-8")
        self.assertEqual(content, "one\nnew\nthree\n")

    def test_full_edit_dry_run(self):
        # Create a few temporary files
        _, file1 = tempfile.mkstemp()

        orig_content = "one\ntwo\nthree\n"

        with open(file1, "w", encoding="utf-8") as f:
            f.write(orig_content)

        files = [file1]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(
            models.GPT4,
            "diff",
            io=InputOutput(dry_run=True),
            openai_api_key="fake_key",
            fnames=files,
            dry_run=True,
        )

        def mock_send(*args, **kwargs):
            coder.partial_response_content = f"""
Do this:

{Path(file1).name}
<<<<<<< ORIGINAL
two
=======
new
>>>>>>> UPDATED

"""
            coder.partial_response_function_call = dict()

        coder.send = MagicMock(side_effect=mock_send)

        # Call the run method with a message
        coder.run(with_message="hi")

        content = Path(file1).read_text(encoding="utf-8")
        self.assertEqual(content, orig_content)


if __name__ == "__main__":
    unittest.main()
