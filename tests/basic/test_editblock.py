# flake8: noqa: E501

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from aider.coders import Coder
from aider.coders import editblock_coder as eb
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.models import Model


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")

    def test_find_filename(self):
        fence = ("```", "```")
        valid_fnames = ["file1.py", "file2.py", "dir/file3.py", r"\windows\__init__.py"]

        # Test with filename on a single line
        lines = ["file1.py", "```"]
        self.assertEqual(eb.find_filename(lines, fence, valid_fnames), "file1.py")

        # Test with filename in fence
        lines = ["```python", "file3.py", "```"]
        self.assertEqual(eb.find_filename(lines, fence, valid_fnames), "dir/file3.py")

        # Test with no valid filename
        lines = ["```", "invalid_file.py", "```"]
        self.assertEqual("invalid_file.py", eb.find_filename(lines, fence, valid_fnames))

        # Test with multiple fences
        lines = ["```python", "file1.py", "```", "```", "file2.py", "```"]
        self.assertEqual(eb.find_filename(lines, fence, valid_fnames), "file2.py")

        # Test with filename having extra characters
        lines = ["# file1.py", "```"]
        self.assertEqual(eb.find_filename(lines, fence, valid_fnames), "file1.py")

        # Test with fuzzy matching
        lines = ["file1_py", "```"]
        self.assertEqual(eb.find_filename(lines, fence, valid_fnames), "file1.py")

        # Test with fuzzy matching
        lines = [r"\windows__init__.py", "```"]
        self.assertEqual(eb.find_filename(lines, fence, valid_fnames), r"\windows\__init__.py")

    # fuzzy logic disabled v0.11.2-dev
    def __test_replace_most_similar_chunk(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line.\n"
        part = "This is a sample text\n"
        replace = "This is a replaced text.\n"
        expected_output = "This is a replaced text.\nAnother line of text.\nYet another line.\n"

        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    # fuzzy logic disabled v0.11.2-dev
    def __test_replace_most_similar_chunk_not_perfect_match(self):
        whole = "This is a sample text.\nAnother line of text.\nYet another line.\n"
        part = "This was a sample text.\nAnother line of txt\n"
        replace = "This is a replaced text.\nModified line of text.\n"
        expected_output = "This is a replaced text.\nModified line of text.\nYet another line.\n"

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
<<<<<<< SEARCH
Two
=======
Tooooo
>>>>>>> REPLACE
```

Hope you like it!
"""

        edits = list(eb.find_original_update_blocks(edit))
        self.assertEqual(edits, [("foo.txt", "Two\n", "Tooooo\n")])

    def test_find_original_update_blocks_mangled_filename_w_source_tag(self):
        source = "source"

        edit = """
Here's the change:

<%s>foo.txt
<<<<<<< SEARCH
One
=======
Two
>>>>>>> REPLACE
</%s>

Hope you like it!
""" % (source, source)

        fence = ("<%s>" % source, "</%s>" % source)

        with self.assertRaises(ValueError) as cm:
            _edits = list(eb.find_original_update_blocks(edit, fence))
        self.assertIn("missing filename", str(cm.exception))

    def test_find_original_update_blocks_quote_below_filename(self):
        edit = """
Here's the change:

foo.txt
```text
<<<<<<< SEARCH
Two
=======
Tooooo
>>>>>>> REPLACE
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
<<<<<<< SEARCH
Two
=======
Tooooo


oops!
"""

        with self.assertRaises(ValueError) as cm:
            list(eb.find_original_update_blocks(edit))
        self.assertIn("Expected `>>>>>>> REPLACE` or `=======`", str(cm.exception))

    def test_find_original_update_blocks_missing_filename(self):
        edit = """
Here's the change:

```text
<<<<<<< SEARCH
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
<<<<<<< SEARCH
            self.console.print("[red]^C again to quit")
=======
            self.io.tool_error("^C again to quit")
>>>>>>> REPLACE

aider/coder.py
<<<<<<< SEARCH
            self.io.tool_error("Malformed ORIGINAL/UPDATE blocks, retrying...")
            self.io.tool_error(err)
=======
            self.io.tool_error("Malformed ORIGINAL/UPDATE blocks, retrying...")
            self.io.tool_error(str(err))
>>>>>>> REPLACE

aider/coder.py
<<<<<<< SEARCH
            self.console.print("[red]Unable to get commit message from gpt-3.5-turbo. Use /commit to try again.\n")
=======
            self.io.tool_error("Unable to get commit message from gpt-3.5-turbo. Use /commit to try again.")
>>>>>>> REPLACE

aider/coder.py
<<<<<<< SEARCH
            self.console.print("[red]Skipped commit.")
=======
            self.io.tool_error("Skipped commit.")
>>>>>>> REPLACE"""

        # Should not raise a ValueError
        list(eb.find_original_update_blocks(edit))

    def test_incomplete_edit_block_missing_filename(self):
        edit = """
No problem! Here are the changes to patch `subprocess.check_output` instead of `subprocess.run` in both tests:

```python
tests/test_repomap.py
<<<<<<< SEARCH
    def test_check_for_ctags_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("ctags not found")
=======
    def test_check_for_ctags_failure(self):
        with patch("subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = Exception("ctags not found")
>>>>>>> REPLACE

<<<<<<< SEARCH
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
>>>>>>> REPLACE
```

These changes replace the `subprocess.run` patches with `subprocess.check_output` patches in both `test_check_for_ctags_failure` and `test_check_for_ctags_success` tests.
"""
        edit_blocks = list(eb.find_original_update_blocks(edit))
        self.assertEqual(len(edit_blocks), 2)  # 2 edits
        self.assertEqual(edit_blocks[0][0], "tests/test_repomap.py")
        self.assertEqual(edit_blocks[1][0], "tests/test_repomap.py")

    def test_replace_part_with_missing_varied_leading_whitespace(self):
        whole = """
    line1
    line2
        line3
    line4
"""

        part = "line2\n    line3\n"
        replace = "new_line2\n    new_line3\n"
        expected_output = """
    line1
    new_line2
        new_line3
    line4
"""

        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_replace_part_with_missing_leading_whitespace(self):
        whole = "    line1\n    line2\n    line3\n"
        part = "line1\nline2\n"
        replace = "new_line1\nnew_line2\n"
        expected_output = "    new_line1\n    new_line2\n    line3\n"

        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_replace_part_with_just_some_missing_leading_whitespace(self):
        whole = "    line1\n    line2\n    line3\n"
        part = " line1\n line2\n"
        replace = " new_line1\n     new_line2\n"
        expected_output = "    new_line1\n        new_line2\n    line3\n"

        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_replace_part_with_missing_leading_whitespace_including_blank_line(self):
        """
        The part has leading whitespace on all lines, so should be ignored.
        But it has a *blank* line with no whitespace at all, which was causing a
        bug per issue #25. Test case to repro and confirm fix.
        """
        whole = "    line1\n    line2\n    line3\n"
        part = "\n  line1\n  line2\n"
        replace = "  new_line1\n  new_line2\n"
        expected_output = "    new_line1\n    new_line2\n    line3\n"

        result = eb.replace_most_similar_chunk(whole, part, replace)
        self.assertEqual(result, expected_output)

    def test_full_edit(self):
        # Create a few temporary files
        _, file1 = tempfile.mkstemp()

        with open(file1, "w", encoding="utf-8") as f:
            f.write("one\ntwo\nthree\n")

        files = [file1]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(self.GPT35, "diff", io=InputOutput(), fnames=files)

        def mock_send(*args, **kwargs):
            coder.partial_response_content = f"""
Do this:

{Path(file1).name}
<<<<<<< SEARCH
two
=======
new
>>>>>>> REPLACE

"""
            coder.partial_response_function_call = dict()
            return []

        coder.send = mock_send

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
            self.GPT35,
            "diff",
            io=InputOutput(dry_run=True),
            fnames=files,
            dry_run=True,
        )

        def mock_send(*args, **kwargs):
            coder.partial_response_content = f"""
Do this:

{Path(file1).name}
<<<<<<< SEARCH
two
=======
new
>>>>>>> REPLACE

"""
            coder.partial_response_function_call = dict()
            return []

        coder.send = mock_send

        # Call the run method with a message
        coder.run(with_message="hi")

        content = Path(file1).read_text(encoding="utf-8")
        self.assertEqual(content, orig_content)

    def test_find_original_update_blocks_mupltiple_same_file(self):
        edit = """
Here's the change:

```text
foo.txt
<<<<<<< SEARCH
one
=======
two
>>>>>>> REPLACE

...

<<<<<<< SEARCH
three
=======
four
>>>>>>> REPLACE
```

Hope you like it!
"""

        edits = list(eb.find_original_update_blocks(edit))
        self.assertEqual(
            edits,
            [
                ("foo.txt", "one\n", "two\n"),
                ("foo.txt", "three\n", "four\n"),
            ],
        )

    def test_deepseek_coder_v2_filename_mangling(self):
        edit = """
Here's the change:

 ```python
foo.txt
```
```python
<<<<<<< SEARCH
one
=======
two
>>>>>>> REPLACE
```

Hope you like it!
"""

        edits = list(eb.find_original_update_blocks(edit))
        self.assertEqual(
            edits,
            [
                ("foo.txt", "one\n", "two\n"),
            ],
        )

    def test_new_file_created_in_same_folder(self):
        edit = """
Here's the change:

path/to/a/file2.txt
```python
<<<<<<< SEARCH
=======
three
>>>>>>> REPLACE
```

another change

path/to/a/file1.txt
```python
<<<<<<< SEARCH
one
=======
two
>>>>>>> REPLACE
```

Hope you like it!
"""

        edits = list(
            eb.find_original_update_blocks(edit, valid_fnames=["path/to/a/file1.txt"])
        )
        self.assertEqual(
            edits,
            [
                ("path/to/a/file2.txt", "", "three\n"),
                ("path/to/a/file1.txt", "one\n", "two\n"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
