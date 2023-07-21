import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import git

from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.repo import GitRepo


class TestRepo(unittest.TestCase):
    @patch("aider.repo.send_with_retries")
    def test_get_commit_message(self, mock_send):
        # Set the return value of the mocked function
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "a good commit message"
        mock_send.return_value = (None, mock_response)

        repo = GitRepo(InputOutput(), None)
        # Call the get_commit_message method with dummy diff and context
        result = repo.get_commit_message("dummy diff", "dummy context")

        # Assert that the returned message is the expected one
        self.assertEqual(result, "a good commit message")

    @patch("aider.repo.send_with_retries")
    def test_get_commit_message_strip_quotes(self, mock_send):
        # Set the return value of the mocked function
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '"a good commit message"'
        mock_send.return_value = (None, mock_response)

        repo = GitRepo(InputOutput(), None)
        # Call the get_commit_message method with dummy diff and context
        result = repo.get_commit_message("dummy diff", "dummy context")

        # Assert that the returned message is the expected one
        self.assertEqual(result, "a good commit message")

    @patch("aider.repo.send_with_retries")
    def test_get_commit_message_no_strip_unmatched_quotes(self, mock_send):
        # Set the return value of the mocked function
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = 'a good "commit message"'
        mock_send.return_value = (None, mock_response)

        repo = GitRepo(InputOutput(), None)
        # Call the get_commit_message method with dummy diff and context
        result = repo.get_commit_message("dummy diff", "dummy context")

        # Assert that the returned message is the expected one
        self.assertEqual(result, 'a good "commit message"')

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

        tracked_files = GitRepo(InputOutput(), [tempdir]).get_tracked_files()

        # On windows, paths will come back \like\this, so normalize them back to Paths
        tracked_files = [Path(fn) for fn in tracked_files]

        # Assert that coder.get_tracked_files() returns the three filenames
        self.assertEqual(set(tracked_files), set(created_files))
