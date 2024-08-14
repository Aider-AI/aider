import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from aider.coders import Coder
from aider.coders.wholefile_coder import WholeFileCoder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.models import Model


class TestWholeFileCoder(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

        self.GPT35 = Model("gpt-3.5-turbo")

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_no_files(self):
        # Initialize WholeFileCoder with the temporary directory
        io = InputOutput(yes=True)

        coder = WholeFileCoder(main_model=self.GPT35, io=io, fnames=[])
        coder.partial_response_content = (
            'To print "Hello, World!" in most programming languages, you can use the following'
            ' code:\n\n```python\nprint("Hello, World!")\n```\n\nThis code will output "Hello,'
            ' World!" to the console.'
        )

        # This is throwing ValueError!
        coder.render_incremental_response(True)

    def test_no_files_new_file_should_ask(self):
        io = InputOutput(yes=False)  # <- yes=FALSE
        coder = WholeFileCoder(main_model=self.GPT35, io=io, fnames=[])
        coder.partial_response_content = (
            'To print "Hello, World!" in most programming languages, you can use the following'
            ' code:\n\nfoo.js\n```python\nprint("Hello, World!")\n```\n\nThis code will output'
            ' "Hello, World!" to the console.'
        )
        coder.update_files()
        self.assertFalse(Path("foo.js").exists())

    def test_update_files(self):
        # Create a sample file in the temporary directory
        sample_file = "sample.txt"
        with open(sample_file, "w") as f:
            f.write("Original content\n")

        # Initialize WholeFileCoder with the temporary directory
        io = InputOutput(yes=True)
        coder = WholeFileCoder(main_model=self.GPT35, io=io, fnames=[sample_file])

        # Set the partial response content with the updated content
        coder.partial_response_content = f"{sample_file}\n```\nUpdated content\n```"

        # Call update_files method
        edited_files = coder.update_files()

        # Check if the sample file was updated
        self.assertIn("sample.txt", edited_files)

        # Check if the content of the sample file was updated
        with open(sample_file, "r") as f:
            updated_content = f.read()
        self.assertEqual(updated_content, "Updated content\n")

    def test_update_files_live_diff(self):
        # Create a sample file in the temporary directory
        sample_file = "sample.txt"
        with open(sample_file, "w") as f:
            f.write("\n".join(map(str, range(0, 100))))

        # Initialize WholeFileCoder with the temporary directory
        io = InputOutput(yes=True)
        coder = WholeFileCoder(main_model=self.GPT35, io=io, fnames=[sample_file])

        # Set the partial response content with the updated content
        coder.partial_response_content = f"{sample_file}\n```\n0\n\1\n2\n"

        lines = coder.get_edits(mode="diff").splitlines()

        # the live diff should be concise, since we haven't changed anything yet
        self.assertLess(len(lines), 20)

    def test_update_files_with_existing_fence(self):
        # Create a sample file in the temporary directory
        sample_file = "sample.txt"
        original_content = """
Here is some quoted text:
```
Quote!
```
"""
        with open(sample_file, "w") as f:
            f.write(original_content)

        # Initialize WholeFileCoder with the temporary directory
        io = InputOutput(yes=True)
        coder = WholeFileCoder(main_model=self.GPT35, io=io, fnames=[sample_file])

        coder.choose_fence()

        self.assertNotEqual(coder.fence[0], "```")

        # Set the partial response content with the updated content
        coder.partial_response_content = (
            f"{sample_file}\n{coder.fence[0]}\nUpdated content\n{coder.fence[1]}"
        )

        # Call update_files method
        edited_files = coder.update_files()

        # Check if the sample file was updated
        self.assertIn("sample.txt", edited_files)

        # Check if the content of the sample file was updated
        with open(sample_file, "r") as f:
            updated_content = f.read()
        self.assertEqual(updated_content, "Updated content\n")

    def test_update_files_bogus_path_prefix(self):
        # Create a sample file in the temporary directory
        sample_file = "sample.txt"
        with open(sample_file, "w") as f:
            f.write("Original content\n")

        # Initialize WholeFileCoder with the temporary directory
        io = InputOutput(yes=True)
        coder = WholeFileCoder(main_model=self.GPT35, io=io, fnames=[sample_file])

        # Set the partial response content with the updated content
        # With path/to/ prepended onto the filename
        coder.partial_response_content = f"path/to/{sample_file}\n```\nUpdated content\n```"

        # Call update_files method
        edited_files = coder.update_files()

        # Check if the sample file was updated
        self.assertIn("sample.txt", edited_files)

        # Check if the content of the sample file was updated
        with open(sample_file, "r") as f:
            updated_content = f.read()
        self.assertEqual(updated_content, "Updated content\n")

    def test_update_files_not_in_chat(self):
        # Create a sample file in the temporary directory
        sample_file = "sample.txt"
        with open(sample_file, "w") as f:
            f.write("Original content\n")

        # Initialize WholeFileCoder with the temporary directory
        io = InputOutput(yes=True)
        coder = WholeFileCoder(main_model=self.GPT35, io=io)

        # Set the partial response content with the updated content
        coder.partial_response_content = f"{sample_file}\n```\nUpdated content\n```"

        # Call update_files method
        edited_files = coder.update_files()

        # Check if the sample file was updated
        self.assertIn("sample.txt", edited_files)

        # Check if the content of the sample file was updated
        with open(sample_file, "r") as f:
            updated_content = f.read()
        self.assertEqual(updated_content, "Updated content\n")

    def test_update_files_no_filename_single_file_in_chat(self):
        sample_file = "accumulate.py"
        content = (
            "def accumulate(collection, operation):\n    return [operation(x) for x in"
            " collection]\n"
        )

        with open(sample_file, "w") as f:
            f.write("Original content\n")

        # Initialize WholeFileCoder with the temporary directory
        io = InputOutput(yes=True)
        coder = WholeFileCoder(main_model=self.GPT35, io=io, fnames=[sample_file])

        # Set the partial response content with the updated content
        coder.partial_response_content = (
            f"Here's the modified `{sample_file}` file that implements the `accumulate`"
            f" function as per the given instructions:\n\n```\n{content}```\n\nThis"
            " implementation uses a list comprehension to apply the `operation` function to"
            " each element of the `collection` and returns the resulting list."
        )

        # Call update_files method
        edited_files = coder.update_files()

        # Check if the sample file was updated
        self.assertIn(sample_file, edited_files)

        # Check if the content of the sample file was updated
        with open(sample_file, "r") as f:
            updated_content = f.read()
        self.assertEqual(updated_content, content)

    def test_update_files_earlier_filename(self):
        fname_a = Path("a.txt")
        fname_b = Path("b.txt")

        fname_a.write_text("before a\n")
        fname_b.write_text("before b\n")

        response = """
Here is a new version of `a.txt` for you to consider:

```
after a
```

And here is `b.txt`:

```
after b
```
"""
        # Initialize WholeFileCoder with the temporary directory
        io = InputOutput(yes=True)
        coder = WholeFileCoder(main_model=self.GPT35, io=io, fnames=[fname_a, fname_b])

        # Set the partial response content with the updated content
        coder.partial_response_content = response

        # Call update_files method
        edited_files = coder.update_files()

        # Check if the sample file was updated
        self.assertIn(str(fname_a), edited_files)
        self.assertIn(str(fname_b), edited_files)

        self.assertEqual(fname_a.read_text(), "after a\n")
        self.assertEqual(fname_b.read_text(), "after b\n")

    def test_update_named_file_but_extra_unnamed_code_block(self):
        sample_file = "hello.py"
        new_content = "new\ncontent\ngoes\nhere\n"

        with open(sample_file, "w") as f:
            f.write("Original content\n")

        # Initialize WholeFileCoder with the temporary directory
        io = InputOutput(yes=True)
        coder = WholeFileCoder(main_model=self.GPT35, io=io, fnames=[sample_file])

        # Set the partial response content with the updated content
        coder.partial_response_content = (
            f"Here's the modified `{sample_file}` file that implements the `accumulate`"
            f" function as per the given instructions:\n\n```\n{new_content}```\n\nThis"
            " implementation uses a list comprehension to apply the `operation` function to"
            " each element of the `collection` and returns the resulting list.\n"
            "Run it like this:\n\n"
            "```\npython {sample_file}\n```\n\n"
        )

        # Call update_files method
        edited_files = coder.update_files()

        # Check if the sample file was updated
        self.assertIn(sample_file, edited_files)

        # Check if the content of the sample file was updated
        with open(sample_file, "r") as f:
            updated_content = f.read()
        self.assertEqual(updated_content, new_content)

    def test_full_edit(self):
        # Create a few temporary files
        _, file1 = tempfile.mkstemp()

        with open(file1, "w", encoding="utf-8") as f:
            f.write("one\ntwo\nthree\n")

        files = [file1]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(self.GPT35, "whole", io=InputOutput(), fnames=files, stream=False)

        # no trailing newline so the response content below doesn't add ANOTHER newline
        new_content = "new\ntwo\nthree"

        def mock_send(*args, **kwargs):
            coder.partial_response_content = f"""
Do this:

{Path(file1).name}
```
{new_content}
```

"""
            coder.partial_response_function_call = dict()
            return []

        coder.send = MagicMock(side_effect=mock_send)

        # Call the run method with a message
        coder.run(with_message="hi")

        content = Path(file1).read_text(encoding="utf-8")

        # check for one trailing newline
        self.assertEqual(content, new_content + "\n")


if __name__ == "__main__":
    unittest.main()
