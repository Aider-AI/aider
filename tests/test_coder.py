import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import git
import openai

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

    def test_allowed_to_edit(self):
        with GitTemporaryDirectory():
            repo = git.Repo(Path.cwd())
            fname = Path("foo.txt")
            fname.touch()
            repo.git.add(str(fname))
            repo.git.commit("-m", "init")

            io = InputOutput(yes=True)
            # Initialize the Coder object with the mocked IO and mocked repo
            coder = Coder.create(models.GPT4, None, io, fnames=["foo.txt"])

            self.assertTrue(coder.allowed_to_edit("foo.txt"))
            self.assertTrue(coder.allowed_to_edit("new.txt"))

    def test_allowed_to_edit_no(self):
        with GitTemporaryDirectory():
            repo = git.Repo(Path.cwd())
            fname = Path("foo.txt")
            fname.touch()
            repo.git.add(str(fname))
            repo.git.commit("-m", "init")

            # say NO
            io = InputOutput(yes=False)

            coder = Coder.create(models.GPT4, None, io, fnames=["foo.txt"])

            self.assertTrue(coder.allowed_to_edit("foo.txt"))
            self.assertFalse(coder.allowed_to_edit("new.txt"))

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
        coder.repo.get_tracked_files = mock

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
        coder.repo.get_tracked_files = mock

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
            coder.repo.get_tracked_files = mock

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
            coder.repo.get_tracked_files = mock

            dump(fname)
            # Call the check_for_file_mentions method
            coder.check_for_file_mentions(f"Please check `{fname}`")

            self.assertEqual(coder.abs_fnames, set([str(fname.resolve())]))

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

    if __name__ == "__main__":
        unittest.main()
