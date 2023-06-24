import os
from pathlib import Path
import tempfile
import unittest

from aider.coders.wholefile_coder import WholeFileCoder
from aider.io import InputOutput

class TestWholeFileCoder(unittest.TestCase):
    def test_update_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a sample file in the temporary directory
            sample_file = os.path.join(temp_dir, "sample.txt")
            with open(sample_file, "w") as f:
                f.write("Original content\n")

            # Initialize WholeFileCoder with the temporary directory
            io = InputOutput()
            coder = WholeFileCoder(root=temp_dir, io=io)

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
