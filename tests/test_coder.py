import unittest
from unittest.mock import MagicMock
from aider.coder import Coder

class TestCoder(unittest.TestCase):
    def test_check_for_file_mentions(self):
        # Mock the IO object
        mock_io = MagicMock()
        mock_io.get_input.return_value = "Please check file1.txt and file2.py"
        mock_io.confirm_ask.return_value = True

        # Initialize the Coder object with the mocked IO
        coder = Coder(io=mock_io, openai_api_key="fake_key")

        # Add sample files to the Coder object
        coder.abs_fnames = {
            "/path/to/repo/file1.txt",
            "/path/to/repo/file2.py",
        }
        coder.root = "/path/to/repo"

        # Call the check_for_file_mentions method
        result = coder.check_for_file_mentions("Please check file1.txt and file2.py")

        # Check if the result is as expected
        self.assertEqual(result, "Added files: file1.txt, file2.py")

if __name__ == "__main__":
    unittest.main()
