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


if __name__ == "__main__":
    unittest.main()
