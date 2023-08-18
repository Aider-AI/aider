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
            repo = git.Repo()

            fname = Path("added.txt")
            fname.touch()
            repo.git.add(str(fname))

            fname = Path("repo.txt")
            fname.touch()
            repo.git.add(str(fname))

            repo.git.commit("-m", "init")

            # YES!
            io = InputOutput(yes=True)
            coder = Coder.create(models.GPT4, None, io, fnames=["added.txt"])

            self.assertTrue(coder.allowed_to_edit("added.txt"))
            self.assertTrue(coder.allowed_to_edit("repo.txt"))
            self.assertTrue(coder.allowed_to_edit("new.txt"))

            self.assertIn("repo.txt", str(coder.abs_fnames))
            self.assertIn("new.txt", str(coder.abs_fnames))

            self.assertFalse(coder.need_commit_before_edits)

    def test_allowed_to_edit_no(self):
        with GitTemporaryDirectory():
            repo = git.Repo()

            fname = Path("added.txt")
            fname.touch()
            repo.git.add(str(fname))

            fname = Path("repo.txt")
            fname.touch()
            repo.git.add(str(fname))

            repo.git.commit("-m", "init")

            # say NO
            io = InputOutput(yes=False)

            coder = Coder.create(models.GPT4, None, io, fnames=["added.txt"])

            self.assertTrue(coder.allowed_to_edit("added.txt"))
            self.assertFalse(coder.allowed_to_edit("repo.txt"))
            self.assertFalse(coder.allowed_to_edit("new.txt"))

            self.assertNotIn("repo.txt", str(coder.abs_fnames))
            self.assertNotIn("new.txt", str(coder.abs_fnames))

            self.assertFalse(coder.need_commit_before_edits)

    def test_allowed_to_edit_dirty(self):
        with GitTemporaryDirectory():
            repo = git.Repo()

            fname = Path("added.txt")
            fname.touch()
            repo.git.add(str(fname))

            repo.git.commit("-m", "init")

            # say NO
            io = InputOutput(yes=False)

            coder = Coder.create(models.GPT4, None, io, fnames=["added.txt"])

            self.assertTrue(coder.allowed_to_edit("added.txt"))
            self.assertFalse(coder.need_commit_before_edits)

            fname.write_text("dirty!")
            self.assertTrue(coder.allowed_to_edit("added.txt"))
            self.assertTrue(coder.need_commit_before_edits)

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

    def test_new_file_edit_one_commit(self):
        """A new file shouldn't get pre-committed before the GPT edit commit"""
        with GitTemporaryDirectory():
            repo = git.Repo()

            fname = Path("file.txt")

            io = InputOutput(yes=True)
            coder = Coder.create(models.GPT4, "diff", io=io, fnames=[str(fname)])

            self.assertTrue(fname.exists())

            # make sure it was not committed
            with self.assertRaises(git.exc.GitCommandError):
                list(repo.iter_commits(repo.active_branch.name))

            def mock_send(*args, **kwargs):
                coder.partial_response_content = f"""
Do this:

{str(fname)}
<<<<<<< HEAD
=======
new
>>>>>>> updated

"""
                coder.partial_response_function_call = dict()

            coder.send = MagicMock(side_effect=mock_send)
            coder.repo.get_commit_message = MagicMock()
            coder.repo.get_commit_message.return_value = "commit message"

            coder.run(with_message="hi")

            content = fname.read_text()
            self.assertEqual(content, "new\n")

            num_commits = len(list(repo.iter_commits(repo.active_branch.name)))
            self.assertEqual(num_commits, 1)

    def test_only_commit_gpt_edited_file(self):
        """
        Only commit file that gpt edits, not other dirty files.
        Also ensure commit msg only depends on diffs from the GPT edited file.
        """

        with GitTemporaryDirectory():
            repo = git.Repo()

            fname1 = Path("file1.txt")
            fname2 = Path("file2.txt")

            fname1.write_text("one\n")
            fname2.write_text("two\n")

            repo.git.add(str(fname1))
            repo.git.add(str(fname2))
            repo.git.commit("-m", "new")

            # DIRTY!
            fname1.write_text("ONE\n")

            io = InputOutput(yes=True)
            coder = Coder.create(models.GPT4, "diff", io=io, fnames=[str(fname1), str(fname2)])

            def mock_send(*args, **kwargs):
                coder.partial_response_content = f"""
Do this:

{str(fname2)}
<<<<<<< HEAD
two
=======
TWO
>>>>>>> updated

"""
                coder.partial_response_function_call = dict()

            def mock_get_commit_message(diffs, context):
                self.assertNotIn("one", diffs)
                self.assertNotIn("ONE", diffs)
                return "commit message"

            coder.send = MagicMock(side_effect=mock_send)
            coder.repo.get_commit_message = MagicMock(side_effect=mock_get_commit_message)

            coder.run(with_message="hi")

            content = fname2.read_text()
            self.assertEqual(content, "TWO\n")

            self.assertTrue(repo.is_dirty(path=str(fname1)))

    def test_gpt_edit_to_dirty_file(self):
        """A dirty file should be committed before the GPT edits are committed"""

        with GitTemporaryDirectory():
            repo = git.Repo()

            fname = Path("file.txt")
            fname.write_text("one\n")
            repo.git.add(str(fname))

            fname2 = Path("other.txt")
            fname2.write_text("other\n")
            repo.git.add(str(fname2))

            repo.git.commit("-m", "new")

            # dirty
            fname.write_text("two\n")
            fname2.write_text("OTHER\n")

            io = InputOutput(yes=True)
            coder = Coder.create(models.GPT4, "diff", io=io, fnames=[str(fname)])

            def mock_send(*args, **kwargs):
                coder.partial_response_content = f"""
Do this:

{str(fname)}
<<<<<<< HEAD
two
=======
three
>>>>>>> updated

"""
                coder.partial_response_function_call = dict()

            saved_diffs = []

            def mock_get_commit_message(diffs, context):
                saved_diffs.append(diffs)
                return "commit message"

            coder.repo.get_commit_message = MagicMock(side_effect=mock_get_commit_message)
            coder.send = MagicMock(side_effect=mock_send)

            coder.run(with_message="hi")

            content = fname.read_text()
            self.assertEqual(content, "three\n")

            num_commits = len(list(repo.iter_commits(repo.active_branch.name)))
            self.assertEqual(num_commits, 3)

            diff = repo.git.diff(["HEAD~2", "HEAD~1"])
            self.assertIn("one", diff)
            self.assertIn("two", diff)
            self.assertNotIn("three", diff)
            self.assertNotIn("other", diff)
            self.assertNotIn("OTHER", diff)

            diff = saved_diffs[0]
            self.assertIn("one", diff)
            self.assertIn("two", diff)
            self.assertNotIn("three", diff)
            self.assertNotIn("other", diff)
            self.assertNotIn("OTHER", diff)

            diff = repo.git.diff(["HEAD~1", "HEAD"])
            self.assertNotIn("one", diff)
            self.assertIn("two", diff)
            self.assertIn("three", diff)
            self.assertNotIn("other", diff)
            self.assertNotIn("OTHER", diff)

            diff = saved_diffs[1]
            self.assertNotIn("one", diff)
            self.assertIn("two", diff)
            self.assertIn("three", diff)
            self.assertNotIn("other", diff)
            self.assertNotIn("OTHER", diff)

            self.assertEqual(len(saved_diffs), 2)

    def test_gpt_edit_to_existing_file_not_in_repo(self):
        with GitTemporaryDirectory():
            repo = git.Repo()

            fname = Path("file.txt")
            fname.write_text("one\n")

            fname2 = Path("other.txt")
            fname2.write_text("other\n")
            repo.git.add(str(fname2))

            repo.git.commit("-m", "initial")

            io = InputOutput(yes=True)
            coder = Coder.create(models.GPT4, "diff", io=io, fnames=[str(fname)])

            def mock_send(*args, **kwargs):
                coder.partial_response_content = f"""
Do this:

{str(fname)}
<<<<<<< HEAD
one
=======
two
>>>>>>> updated

"""
                coder.partial_response_function_call = dict()

            saved_diffs = []

            def mock_get_commit_message(diffs, context):
                saved_diffs.append(diffs)
                return "commit message"

            coder.repo.get_commit_message = MagicMock(side_effect=mock_get_commit_message)
            coder.send = MagicMock(side_effect=mock_send)

            coder.run(with_message="hi")

            content = fname.read_text()
            self.assertEqual(content, "two\n")

            diff = saved_diffs[0]
            self.assertIn("file.txt", diff)


if __name__ == "__main__":
    unittest.main()
