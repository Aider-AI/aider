import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import openai
import requests

from aider import models
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput


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
        mock_repo.git.ls_files.return_value = "file1.txt\nother/file1.txt"
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

    def test_run_with_file_deletion(self):
        # Create a few temporary files

        tempdir = Path(tempfile.mkdtemp())

        file1 = tempdir / "file1.txt"
        file2 = tempdir / "file2.txt"

        file1.touch()
        file2.touch()

        files = [file1, file2]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(
            models.GPT4, None, io=InputOutput(), openai_api_key="fake_key", fnames=files
        )

        def mock_send(*args, **kwargs):
            coder.partial_response_content = "ok"
            coder.partial_response_function_call = dict()

        coder.send = MagicMock(side_effect=mock_send)

        # Call the run method with a message
        coder.run(with_message="hi")
        self.assertEqual(len(coder.abs_fnames), 2)

        file1.unlink()

        # Call the run method again with a message
        coder.run(with_message="hi")
        self.assertEqual(len(coder.abs_fnames), 1)

    def test_run_with_file_unicode_error(self):
        # Create a few temporary files
        _, file1 = tempfile.mkstemp()
        _, file2 = tempfile.mkstemp()

        files = [file1, file2]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(
            models.GPT4, None, io=InputOutput(), openai_api_key="fake_key", fnames=files
        )

        def mock_send(*args, **kwargs):
            coder.partial_response_content = "ok"
            coder.partial_response_function_call = dict()

        coder.send = MagicMock(side_effect=mock_send)

        # Call the run method with a message
        coder.run(with_message="hi")
        self.assertEqual(len(coder.abs_fnames), 2)

        # Write some non-UTF8 text into the file
        with open(file1, "wb") as f:
            f.write(b"\x80abc")

        # Call the run method again with a message
        coder.run(with_message="hi")
        self.assertEqual(len(coder.abs_fnames), 1)

    def test_choose_fence(self):
        # Create a few temporary files
        _, file1 = tempfile.mkstemp()

        with open(file1, "wb") as f:
            f.write(b"this contains ``` backticks")

        files = [file1]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(
            models.GPT4, None, io=InputOutput(), openai_api_key="fake_key", fnames=files
        )

        def mock_send(*args, **kwargs):
            coder.partial_response_content = "ok"
            coder.partial_response_function_call = dict()

        coder.send = MagicMock(side_effect=mock_send)

        # Call the run method with a message
        coder.run(with_message="hi")

        self.assertNotEqual(coder.fence[0], "```")

    def test_run_with_file_utf_unicode_error(self):
        "make sure that we honor InputOutput(encoding) and don't just assume utf-8"
        # Create a few temporary files
        _, file1 = tempfile.mkstemp()
        _, file2 = tempfile.mkstemp()

        files = [file1, file2]

        encoding = "utf-16"

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(
            models.GPT4,
            None,
            io=InputOutput(encoding=encoding),
            openai_api_key="fake_key",
            fnames=files,
        )

        def mock_send(*args, **kwargs):
            coder.partial_response_content = "ok"
            coder.partial_response_function_call = dict()

        coder.send = MagicMock(side_effect=mock_send)

        # Call the run method with a message
        coder.run(with_message="hi")
        self.assertEqual(len(coder.abs_fnames), 2)

        some_content_which_will_error_if_read_with_encoding_utf8 = "ÅÍÎÏ".encode(encoding)
        with open(file1, "wb") as f:
            f.write(some_content_which_will_error_if_read_with_encoding_utf8)

        coder.run(with_message="hi")

        # both files should still be here
        self.assertEqual(len(coder.abs_fnames), 2)

    if __name__ == "__main__":
        unittest.main()
