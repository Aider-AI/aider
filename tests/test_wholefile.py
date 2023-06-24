import os
import tempfile
import unittest

from aider import models
from aider.coders.wholefile_coder import WholeFileCoder
from aider.io import InputOutput


class TestWholeFileCoder(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.original_cwd)

    def test_update_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Create a sample file in the temporary directory
            sample_file = "sample.txt"
            with open(sample_file, "w") as f:
                f.write("Original content\n")

            # Initialize WholeFileCoder with the temporary directory
            io = InputOutput(yes=True)
            coder = WholeFileCoder(main_model=models.GPT35, io=io, fnames=[sample_file])

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

    def test_update_files_not_in_chat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            # Create a sample file in the temporary directory
            sample_file = "sample.txt"
            with open(sample_file, "w") as f:
                f.write("Original content\n")

            # Initialize WholeFileCoder with the temporary directory
            io = InputOutput(yes=True)
            coder = WholeFileCoder(main_model=models.GPT35, io=io)

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

    def test_update_files_earlier_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            sample_file = "accumulate.py"
            content = (
                "def accumulate(collection, operation):\n    return [operation(x) for x in"
                " collection]\n"
            )

            with open(sample_file, "w") as f:
                f.write("Original content\n")

            # Initialize WholeFileCoder with the temporary directory
            io = InputOutput(yes=True)
            coder = WholeFileCoder(main_model=models.GPT35, io=io, fnames=[sample_file])

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


if __name__ == "__main__":
    unittest.main()
