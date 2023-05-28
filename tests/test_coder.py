import os
import unittest
from unittest.mock import MagicMock
from aider.coder import Coder


class TestCoder(unittest.TestCase):
    def test_check_for_file_mentions(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder(io=mock_io, openai_api_key="fake_key")

        # Mock the git repo
        mock_repo = MagicMock()
        mock_repo.git.ls_files.return_value = "file1.txt\nfile2.py"
        coder.repo = mock_repo

        # Call the check_for_file_mentions method
        coder.check_for_file_mentions("Please check file1.txt and file2.py")

        # Check if coder.abs_fnames contains both files
        expected_files = {os.path.abspath("file1.txt"), os.path.abspath("file2.py")}
        self.assertEqual(coder.abs_fnames, expected_files)

    def test_check_for_filename_mentions_of_longer_paths(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder(io=mock_io, openai_api_key="fake_key")

        # Mock the git repo
        mock_repo = MagicMock()
        mock_repo.git.ls_files.return_value = "./file1.txt\n./file2.py"
        coder.repo = mock_repo

        # Call the check_for_file_mentions method
        coder.check_for_file_mentions("Please check file1.txt and file2.py")

        # Check if coder.abs_fnames contains both files
        expected_files = {os.path.abspath("file1.txt"), os.path.abspath("file2.py")}
        self.assertEqual(coder.abs_fnames, expected_files)

    def test_check_for_ambiguous_filename_mentions_of_longer_paths(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder(io=mock_io, openai_api_key="fake_key")

        # Mock the git repo
        mock_repo = MagicMock()
        mock_repo.git.ls_files.return_value = "./file1.txt\n./other/file1.txt"
        coder.repo = mock_repo

        # Call the check_for_file_mentions method
        coder.check_for_file_mentions("Please check file1.txt!")

        self.assertEqual(coder.abs_fnames, set())

    def test_get_commit_message(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder(io=mock_io, openai_api_key="fake_key")

        # Mock the send method to return a tuple with a message and False
        coder.send = MagicMock(return_value=("a good commit message", False))

        # Call the get_commit_message method with dummy diff and context
        result = coder.get_commit_message("dummy diff", "dummy context")

        # Assert that the returned message is the expected one
        self.assertEqual(result, "a good commit message")

if __name__ == "__main__":
    unittest.main()
