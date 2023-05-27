import unittest
from unittest.mock import MagicMock
from aider.coder import Coder

class TestCoder(unittest.TestCase):
    def test_check_for_file_mentions(self):
        # Mock the IO object
        mock_io = MagicMock()
        mock_io.get_input.return_value = "Please check file1.txt and file2.py"
        mock_io.confirm_ask.return_value = True

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder(io=mock_io, openai_api_key="fake_key")

        # Mock the git repo
        mock_repo = MagicMock()
        mock_repo.git.ls_files.return_value = "file1.txt\nfile2.py"
        coder.repo = mock_repo

        # Call the check_for_file_mentions method
        result = coder.check_for_file_mentions("Please check file1.txt and file2.py")

        # Check if coder.abs_fnames contains both files
        expected_files = {os.path.abspath("file1.txt"), os.path.abspath("file2.py")}
        self.assertEqual(coder.abs_fnames, expected_files)

if __name__ == "__main__":
    unittest.main()
