import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import git
import openai
import requests

from aider import models
from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from tests.utils import GitTemporaryDirectory


class TestCoder(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("aider.coders.base_coder.check_model_availability")
        self.mock_check = self.patcher.start()
        self.mock_check.return_value = True

    def tearDown(self):
        self.patcher.stop()

    def test_get_last_modified(self):
        # Mock the IO object
        mock_io = MagicMock()

        with GitTemporaryDirectory():
            repo = git.Repo(Path.cwd())
            fname = Path("new.txt")
            fname.touch()
            repo.git.add(str(fname))
            repo.git.commit("-m", "new")

            # Initialize the Coder object with the mocked IO and mocked repo
            coder = Coder.create(models.GPT4, None, mock_io)

            mod = coder.get_last_modified()

            fname.write_text("hi")
            mod_newer = coder.get_last_modified()
            self.assertLess(mod, mod_newer)

            fname.unlink()
            self.assertEqual(coder.get_last_modified(), 0)

    def test_should_dirty_commit(self):
        # Mock the IO object
        mock_io = MagicMock()

        with GitTemporaryDirectory():
            repo = git.Repo(Path.cwd())
            fname = Path("new.txt")
            fname.touch()
            repo.git.add(str(fname))
            repo.git.commit("-m", "new")

            # Initialize the Coder object with the mocked IO and mocked repo
            coder = Coder.create(models.GPT4, None, mock_io)

            fname.write_text("hi")
            self.assertTrue(coder.should_dirty_commit("hi"))

            self.assertFalse(coder.should_dirty_commit("/exit"))
            self.assertFalse(coder.should_dirty_commit("/help"))

    def test_check_for_file_mentions(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, mock_io)

        # Mock the git repo
        mock = MagicMock()
        mock.return_value = set(["file1.txt", "file2.py"])
        coder.get_tracked_files = mock

        # Call the check_for_file_mentions method
        coder.check_for_file_mentions("Please check file1.txt and file2.py")

        # Check if coder.abs_fnames contains both files
        expected_files = set(
            map(
                str,
                [
                    Path(coder.root) / "file1.txt",
                    Path(coder.root) / "file2.py",
                ],
            )
        )
        self.assertEqual(coder.abs_fnames, expected_files)

    def test_get_files_content(self):
        tempdir = Path(tempfile.mkdtemp())

        file1 = tempdir / "file1.txt"
        file2 = tempdir / "file2.txt"

        file1.touch()
        file2.touch()

        files = [file1, file2]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, io=InputOutput(), fnames=files)

        content = coder.get_files_content().splitlines()
        self.assertIn("file1.txt", content)
        self.assertIn("file2.txt", content)

    def test_check_for_filename_mentions_of_longer_paths(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, mock_io)

        mock = MagicMock()
        mock.return_value = set(["file1.txt", "file2.py"])
        coder.get_tracked_files = mock

        # Call the check_for_file_mentions method
        coder.check_for_file_mentions("Please check file1.txt and file2.py")

        # Check if coder.abs_fnames contains both files
        expected_files = set(
            map(
                str,
                [
                    Path(coder.root) / "file1.txt",
                    Path(coder.root) / "file2.py",
                ],
            )
        )
        self.assertEqual(coder.abs_fnames, expected_files)

    def test_check_for_ambiguous_filename_mentions_of_longer_paths(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, yes=True)
            coder = Coder.create(models.GPT4, None, io)

            fname = Path("file1.txt")
            fname.touch()

            other_fname = Path("other") / "file1.txt"
            other_fname.parent.mkdir(parents=True, exist_ok=True)
            other_fname.touch()

            mock = MagicMock()
            mock.return_value = set([str(fname), str(other_fname)])
            coder.get_tracked_files = mock

            # Call the check_for_file_mentions method
            coder.check_for_file_mentions(f"Please check {fname}!")

            self.assertEqual(coder.abs_fnames, set([str(fname.resolve())]))

    def test_check_for_subdir_mention(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, yes=True)
            coder = Coder.create(models.GPT4, None, io)

            fname = Path("other") / "file1.txt"
            fname.parent.mkdir(parents=True, exist_ok=True)
            fname.touch()

            mock = MagicMock()
            mock.return_value = set([str(fname)])
            coder.get_tracked_files = mock

            dump(fname)
            # Call the check_for_file_mentions method
            coder.check_for_file_mentions(f"Please check `{fname}`")

            self.assertEqual(coder.abs_fnames, set([str(fname.resolve())]))

    def test_get_commit_message(self):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, mock_io)

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
        coder = Coder.create(models.GPT4, None, mock_io)

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
        coder = Coder.create(models.GPT4, None, mock_io)

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
        coder = Coder.create(models.GPT4, None, mock_io)

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
        coder = Coder.create(models.GPT4, None, mock_io)

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
        coder = Coder.create(models.GPT4, None, io=InputOutput(), fnames=files)

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
        coder = Coder.create(models.GPT4, None, io=InputOutput(), fnames=files)

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
        coder = Coder.create(models.GPT4, None, io=InputOutput(), fnames=files)

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

    @patch("aider.coders.base_coder.openai.ChatCompletion.create")
    def test_run_with_invalid_request_error(self, mock_chat_completion_create):
        # Mock the IO object
        mock_io = MagicMock()

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(models.GPT4, None, mock_io)

        # Set up the mock to raise InvalidRequestError
        mock_chat_completion_create.side_effect = openai.error.InvalidRequestError(
            "Invalid request", "param"
        )

        # Call the run method and assert that InvalidRequestError is raised
        with self.assertRaises(openai.error.InvalidRequestError):
            coder.run(with_message="hi")

    def test_get_tracked_files(self):
        # Create a temporary directory
        tempdir = Path(tempfile.mkdtemp())

        # Initialize a git repository in the temporary directory and set user name and email
        repo = git.Repo.init(tempdir)
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "testuser@example.com").release()

        # Create three empty files and add them to the git repository
        filenames = ["README.md", "subdir/fänny.md", "systemüber/blick.md", 'file"with"quotes.txt']
        created_files = []
        for filename in filenames:
            file_path = tempdir / filename
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.touch()
                repo.git.add(str(file_path))
                created_files.append(Path(filename))
            except OSError:
                # windows won't allow files with quotes, that's ok
                self.assertIn('"', filename)
                self.assertEqual(os.name, "nt")

        self.assertTrue(len(created_files) >= 3)

        repo.git.commit("-m", "added")

        # Create a Coder object on the temporary directory
        coder = Coder.create(
            models.GPT4,
            None,
            io=InputOutput(),
            fnames=[str(tempdir / filenames[0])],
        )

        tracked_files = coder.get_tracked_files()

        # On windows, paths will come back \like\this, so normalize them back to Paths
        tracked_files = [Path(fn) for fn in tracked_files]

        # Assert that coder.get_tracked_files() returns the three filenames
        self.assertEqual(set(tracked_files), set(created_files))

    if __name__ == "__main__":
        unittest.main()
