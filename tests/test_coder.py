import os
import unittest
from unittest.mock import MagicMock, patch

import openai
import requests

from aider import models
from aider.coders import Coder


class TestCoder(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("aider.coders.base_coder.check_model_availability")
        self.mock_check = self.patcher.start()
        self.mock_check.return_value = True

    def tearDown(self):
        self.patcher.stop()

    def test_check_for_file_mentions(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, mock_io, openai_api_key="fake_key")

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
        coder = Coder.create(models.GPT4, None, mock_io, openai_api_key="fake_key")

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
        coder = Coder.create(models.GPT4, None, mock_io, openai_api_key="fake_key")

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
        coder = Coder.create(models.GPT4, None, mock_io, openai_api_key="fake_key")

        # Mock the send method to set partial_response_content and return False
        def mock_send(*args, **kwargs):
            coder.partial_response_content = "a good commit message"
            return False

        coder.send = MagicMock(side_effect=mock_send)

        # Call the get_commit_message method with dummy diff and context
        result = coder.get_commit_message("dummy diff", "dummy context")

        # Assert that the returned message is the expected one
        self.assertEqual(result, "a good commit message")

    def test_get_commit_message_strip_quotes(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, mock_io, openai_api_key="fake_key")

        # Mock the send method to set partial_response_content and return False
        def mock_send(*args, **kwargs):
            coder.partial_response_content = "a good commit message"
            return False

        coder.send = MagicMock(side_effect=mock_send)

        # Call the get_commit_message method with dummy diff and context
        result = coder.get_commit_message("dummy diff", "dummy context")

        # Assert that the returned message is the expected one
        self.assertEqual(result, "a good commit message")

    def test_get_commit_message_no_strip_unmatched_quotes(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, mock_io, openai_api_key="fake_key")

        # Mock the send method to set partial_response_content and return False
        def mock_send(*args, **kwargs):
            coder.partial_response_content = 'a good "commit message"'
            return False

        coder.send = MagicMock(side_effect=mock_send)

        # Call the get_commit_message method with dummy diff and context
        result = coder.get_commit_message("dummy diff", "dummy context")

        # Assert that the returned message is the expected one
        self.assertEqual(result, 'a good "commit message"')

    @patch("aider.coders.base_coder.openai.ChatCompletion.create")
    @patch("builtins.print")
    def test_send_with_retries_rate_limit_error(self, mock_print, mock_chat_completion_create):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, mock_io, openai_api_key="fake_key")

        # Set up the mock to raise RateLimitError on
        # the first call and return None on the second call
        mock_chat_completion_create.side_effect = [
            openai.error.RateLimitError("Rate limit exceeded"),
            None,
        ]

        # Call the send_with_retries method
        coder.send_with_retries("model", ["message"], None)

        # Assert that print was called once
        mock_print.assert_called_once()

    @patch("aider.coders.base_coder.openai.ChatCompletion.create")
    @patch("builtins.print")
    def test_send_with_retries_connection_error(self, mock_print, mock_chat_completion_create):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, mock_io, openai_api_key="fake_key")

        # Set up the mock to raise ConnectionError on the first call
        # and return None on the second call
        mock_chat_completion_create.side_effect = [
            requests.exceptions.ConnectionError("Connection error"),
            None,
        ]

        # Call the send_with_retries method
        coder.send_with_retries("model", ["message"], None)

        # Assert that print was called once
        mock_print.assert_called_once()


if __name__ == "__main__":
    unittest.main()
