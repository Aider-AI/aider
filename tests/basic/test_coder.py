import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import git

from aider.coders import Coder
from aider.coders.base_coder import FinishReasonLength, UnknownEditFormat
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo
from aider.sendchat import sanity_check_messages
from aider.utils import GitTemporaryDirectory


class TestCoder(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")
        self.webbrowser_patcher = patch("aider.io.webbrowser.open")
        self.mock_webbrowser = self.webbrowser_patcher.start()

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
            # Use a completely mocked IO object instead of a real one
            io = MagicMock()
            io.confirm_ask = MagicMock(return_value=True)
            coder = Coder.create(self.GPT35, None, io, fnames=["added.txt"])

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

            coder = Coder.create(self.GPT35, None, io, fnames=["added.txt"])

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

            coder = Coder.create(self.GPT35, None, io, fnames=["added.txt"])

            self.assertTrue(coder.allowed_to_edit("added.txt"))
            self.assertFalse(coder.need_commit_before_edits)

            fname.write_text("dirty!")
            self.assertTrue(coder.allowed_to_edit("added.txt"))
            self.assertTrue(coder.need_commit_before_edits)

    def test_get_files_content(self):
        tempdir = Path(tempfile.mkdtemp())

        file1 = tempdir / "file1.txt"
        file2 = tempdir / "file2.txt"

        file1.touch()
        file2.touch()

        files = [file1, file2]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(self.GPT35, None, io=InputOutput(), fnames=files)

        content = coder.get_files_content().splitlines()
        self.assertIn("file1.txt", content)
        self.assertIn("file2.txt", content)

    def test_check_for_filename_mentions(self):
        with GitTemporaryDirectory():
            repo = git.Repo()

            mock_io = MagicMock()

            fname1 = Path("file1.txt")
            fname2 = Path("file2.py")

            fname1.write_text("one\n")
            fname2.write_text("two\n")

            repo.git.add(str(fname1))
            repo.git.add(str(fname2))
            repo.git.commit("-m", "new")

            # Initialize the Coder object with the mocked IO and mocked repo
            coder = Coder.create(self.GPT35, None, mock_io)

            # Call the check_for_file_mentions method
            coder.check_for_file_mentions("Please check file1.txt and file2.py")

            # Check if coder.abs_fnames contains both files
            expected_files = set(
                [
                    str(Path(coder.root) / fname1),
                    str(Path(coder.root) / fname2),
                ]
            )

            self.assertEqual(coder.abs_fnames, expected_files)

    def test_check_for_ambiguous_filename_mentions_of_longer_paths(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)

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

    def test_skip_duplicate_basename_mentions(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)

            # Create files with same basename in different directories
            fname1 = Path("dir1") / "file.txt"
            fname2 = Path("dir2") / "file.txt"
            fname3 = Path("dir3") / "unique.txt"

            for fname in [fname1, fname2, fname3]:
                fname.parent.mkdir(parents=True, exist_ok=True)
                fname.touch()

            # Add one file to chat
            coder.add_rel_fname(str(fname1))

            # Mock get_tracked_files to return all files
            mock = MagicMock()
            mock.return_value = set([str(fname1), str(fname2), str(fname3)])
            coder.repo.get_tracked_files = mock

            # Check that file mentions of a pure basename skips files with duplicate basenames
            mentioned = coder.get_file_mentions(f"Check {fname2.name} and {fname3}")
            self.assertEqual(mentioned, {str(fname3)})

            # Add a read-only file with same basename
            coder.abs_read_only_fnames.add(str(fname2.resolve()))
            mentioned = coder.get_file_mentions(f"Check {fname1} and {fname3}")
            self.assertEqual(mentioned, {str(fname3)})

    def test_check_for_file_mentions_read_only(self):
        with GitTemporaryDirectory():
            io = InputOutput(
                pretty=False,
                yes=True,
            )
            coder = Coder.create(self.GPT35, None, io)

            fname = Path("readonly_file.txt")
            fname.touch()

            coder.abs_read_only_fnames.add(str(fname.resolve()))

            # Mock the get_tracked_files method
            mock = MagicMock()
            mock.return_value = set([str(fname)])
            coder.repo.get_tracked_files = mock

            # Call the check_for_file_mentions method
            result = coder.check_for_file_mentions(f"Please check {fname}!")

            # Assert that the method returns None (user not asked to add the file)
            self.assertIsNone(result)

            # Assert that abs_fnames is still empty (file not added)
            self.assertEqual(coder.abs_fnames, set())

    def test_check_for_file_mentions_with_mocked_confirm(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False)
            coder = Coder.create(self.GPT35, None, io)

            # Mock get_file_mentions to return two file names
            coder.get_file_mentions = MagicMock(return_value=set(["file1.txt", "file2.txt"]))

            # Mock confirm_ask to return False for the first call and True for the second
            io.confirm_ask = MagicMock(side_effect=[False, True, True])

            # First call to check_for_file_mentions
            coder.check_for_file_mentions("Please check file1.txt for the info")

            # Assert that confirm_ask was called twice
            self.assertEqual(io.confirm_ask.call_count, 2)

            # Assert that only file2.txt was added to abs_fnames
            self.assertEqual(len(coder.abs_fnames), 1)
            self.assertIn("file2.txt", str(coder.abs_fnames))

            # Reset the mock
            io.confirm_ask.reset_mock()

            # Second call to check_for_file_mentions
            coder.check_for_file_mentions("Please check file1.txt and file2.txt again")

            # Assert that confirm_ask was called only once (for file1.txt)
            self.assertEqual(io.confirm_ask.call_count, 1)

            # Assert that abs_fnames still contains only file2.txt
            self.assertEqual(len(coder.abs_fnames), 1)
            self.assertIn("file2.txt", str(coder.abs_fnames))

            # Assert that file1.txt is in ignore_mentions
            self.assertIn("file1.txt", coder.ignore_mentions)

    def test_check_for_subdir_mention(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)

            fname = Path("other") / "file1.txt"
            fname.parent.mkdir(parents=True, exist_ok=True)
            fname.touch()

            mock = MagicMock()
            mock.return_value = set([str(fname)])
            coder.repo.get_tracked_files = mock

            # Call the check_for_file_mentions method
            coder.check_for_file_mentions(f"Please check `{fname}`")

            self.assertEqual(coder.abs_fnames, set([str(fname.resolve())]))

    def test_get_file_mentions_various_formats(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)

            # Create test files
            test_files = [
                "file1.txt",
                "file2.py",
                "dir/nested_file.js",
                "dir/subdir/deep_file.html",
                "file99.txt",
                "special_chars!@#.md",
            ]

            # Pre-format the Windows path to avoid backslash issues in f-string expressions
            windows_path = test_files[2].replace("/", "\\")
            win_path3 = test_files[3].replace("/", "\\")

            for fname in test_files:
                fpath = Path(fname)
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.touch()

            # Mock get_addable_relative_files to return our test files
            coder.get_addable_relative_files = MagicMock(return_value=set(test_files))

            # Test different mention formats
            test_cases = [
                # Simple plain text mentions
                (f"You should edit {test_files[0]} first", {test_files[0]}),
                # Multiple files in plain text
                (
                    f"Edit both {test_files[0]} and {test_files[1]}",
                    {test_files[0], test_files[1]},
                ),
                # Files in backticks
                (f"Check the file `{test_files[2]}`", {test_files[2]}),
                # Files in code blocks
                (f"```\n{test_files[3]}\n```", {test_files[3]}),
                # Files in code blocks with language specifier
                # (
                #    f"```python\nwith open('{test_files[1]}', 'r') as f:\n"
                #    f"    data = f.read()\n```",
                #    {test_files[1]},
                # ),
                # Files with Windows-style paths
                (f"Edit the file {windows_path}", {test_files[2]}),
                # Files with different quote styles
                (f'Check "{test_files[5]}" now', {test_files[5]}),
                # All files in one complex message
                (
                    (
                        f"First, edit `{test_files[0]}`. Then modify {test_files[1]}.\n"
                        f"```js\n// Update this file\nconst file = '{test_files[2]}';\n```\n"
                        f"Finally check {win_path3}"
                    ),
                    {test_files[0], test_files[1], test_files[2], test_files[3]},
                ),
                # Files mentioned in markdown bold format
                (f"You should check **{test_files[0]}** for issues", {test_files[0]}),
                (
                    f"Look at both **{test_files[1]}** and **{test_files[2]}**",
                    {test_files[1], test_files[2]},
                ),
                (
                    f"The file **{win_path3}** needs updating",
                    {test_files[3]},
                ),
                (
                    f"Files to modify:\n- **{test_files[0]}**\n- **{test_files[4]}**",
                    {test_files[0], test_files[4]},
                ),
            ]

            for content, expected_mentions in test_cases:
                with self.subTest(content=content):
                    mentioned_files = coder.get_file_mentions(content)
                    self.assertEqual(
                        mentioned_files,
                        expected_mentions,
                        f"Failed to extract mentions from: {content}",
                    )

    def test_get_file_mentions_multiline_backticks(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)

            # Create test files
            test_files = [
                "swebench/harness/test_spec/python.py",
                "swebench/harness/test_spec/javascript.py",
            ]
            for fname in test_files:
                fpath = Path(fname)
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.touch()

            # Mock get_addable_relative_files to return our test files
            coder.get_addable_relative_files = MagicMock(return_value=set(test_files))

            # Input text with multiline backticked filenames
            content = """
Could you please **add the following files to the chat**?

1.  `swebench/harness/test_spec/python.py`
2.  `swebench/harness/test_spec/javascript.py`

Once I have these, I can show you precisely how to do the thing.
"""
            expected_mentions = {
                "swebench/harness/test_spec/python.py",
                "swebench/harness/test_spec/javascript.py",
            }

            mentioned_files = coder.get_file_mentions(content)
            self.assertEqual(
                mentioned_files,
                expected_mentions,
                f"Failed to extract mentions from multiline backticked content: {content}",
            )

    def test_get_file_mentions_path_formats(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)

            # Test cases with different path formats
            test_cases = [
                # Unix paths in content, Unix paths in get_addable_relative_files
                ("Check file1.txt and dir/file2.txt", ["file1.txt", "dir/file2.txt"]),
                # Windows paths in content, Windows paths in get_addable_relative_files
                ("Check file1.txt and dir\\file2.txt", ["file1.txt", "dir\\file2.txt"]),
                # Unix paths in content, Windows paths in get_addable_relative_files
                ("Check file1.txt and dir/file2.txt", ["file1.txt", "dir\\file2.txt"]),
                # Windows paths in content, Unix paths in get_addable_relative_files
                ("Check file1.txt and dir\\file2.txt", ["file1.txt", "dir/file2.txt"]),
                # Mixed paths in content, Unix paths in get_addable_relative_files
                (
                    "Check file1.txt, dir/file2.txt, and other\\file3.txt",
                    ["file1.txt", "dir/file2.txt", "other/file3.txt"],
                ),
                # Mixed paths in content, Windows paths in get_addable_relative_files
                (
                    "Check file1.txt, dir/file2.txt, and other\\file3.txt",
                    ["file1.txt", "dir\\file2.txt", "other\\file3.txt"],
                ),
            ]

            for content, addable_files in test_cases:
                with self.subTest(content=content, addable_files=addable_files):
                    coder.get_addable_relative_files = MagicMock(return_value=set(addable_files))
                    mentioned_files = coder.get_file_mentions(content)
                    expected_files = set(addable_files)
                    self.assertEqual(
                        mentioned_files,
                        expected_files,
                        f"Failed for content: {content}, addable_files: {addable_files}",
                    )

    def test_run_with_file_deletion(self):
        # Create a few temporary files

        tempdir = Path(tempfile.mkdtemp())

        file1 = tempdir / "file1.txt"
        file2 = tempdir / "file2.txt"

        file1.touch()
        file2.touch()

        files = [file1, file2]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(self.GPT35, None, io=InputOutput(), fnames=files)

        def mock_send(*args, **kwargs):
            coder.partial_response_content = "ok"
            coder.partial_response_function_call = dict()
            return []

        coder.send = mock_send

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
        coder = Coder.create(self.GPT35, None, io=InputOutput(), fnames=files)

        def mock_send(*args, **kwargs):
            coder.partial_response_content = "ok"
            coder.partial_response_function_call = dict()
            return []

        coder.send = mock_send

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
            f.write(b"this contains\n```\nbackticks")

        files = [file1]

        # Initialize the Coder object with the mocked IO and mocked repo
        coder = Coder.create(self.GPT35, None, io=InputOutput(), fnames=files)

        def mock_send(*args, **kwargs):
            coder.partial_response_content = "ok"
            coder.partial_response_function_call = dict()
            return []

        coder.send = mock_send

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
            self.GPT35,
            None,
            io=InputOutput(encoding=encoding),
            fnames=files,
        )

        def mock_send(*args, **kwargs):
            coder.partial_response_content = "ok"
            coder.partial_response_function_call = dict()
            return []

        coder.send = mock_send

        # Call the run method with a message
        coder.run(with_message="hi")
        self.assertEqual(len(coder.abs_fnames), 2)

        some_content_which_will_error_if_read_with_encoding_utf8 = "ÅÍÎÏ".encode(encoding)
        with open(file1, "wb") as f:
            f.write(some_content_which_will_error_if_read_with_encoding_utf8)

        coder.run(with_message="hi")

        # both files should still be here
        self.assertEqual(len(coder.abs_fnames), 2)

    def test_new_file_edit_one_commit(self):
        """A new file should get pre-committed before the GPT edit commit"""
        with GitTemporaryDirectory():
            repo = git.Repo()

            fname = Path("file.txt")

            io = InputOutput(yes=True)
            io.tool_warning = MagicMock()
            coder = Coder.create(self.GPT35, "diff", io=io, fnames=[str(fname)])

            self.assertTrue(fname.exists())

            # make sure it was not committed
            with self.assertRaises(git.exc.GitCommandError):
                list(repo.iter_commits(repo.active_branch.name))

            def mock_send(*args, **kwargs):
                coder.partial_response_content = f"""
Do this:

{str(fname)}
<<<<<<< SEARCH
=======
new
>>>>>>> REPLACE

"""
                coder.partial_response_function_call = dict()
                return []

            coder.send = mock_send
            coder.repo.get_commit_message = MagicMock()
            coder.repo.get_commit_message.return_value = "commit message"

            coder.run(with_message="hi")

            content = fname.read_text()
            self.assertEqual(content, "new\n")

            num_commits = len(list(repo.iter_commits(repo.active_branch.name)))
            self.assertEqual(num_commits, 2)

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
            coder = Coder.create(self.GPT35, "diff", io=io, fnames=[str(fname1), str(fname2)])

            def mock_send(*args, **kwargs):
                coder.partial_response_content = f"""
Do this:

{str(fname2)}
<<<<<<< SEARCH
two
=======
TWO
>>>>>>> REPLACE

"""
                coder.partial_response_function_call = dict()
                return []

            def mock_get_commit_message(diffs, context, user_language=None):
                self.assertNotIn("one", diffs)
                self.assertNotIn("ONE", diffs)
                return "commit message"

            coder.send = mock_send
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
            coder = Coder.create(self.GPT35, "diff", io=io, fnames=[str(fname)])

            def mock_send(*args, **kwargs):
                coder.partial_response_content = f"""
Do this:

{str(fname)}
<<<<<<< SEARCH
two
=======
three
>>>>>>> REPLACE

"""
                coder.partial_response_function_call = dict()
                return []

            saved_diffs = []

            def mock_get_commit_message(diffs, context, user_language=None):
                saved_diffs.append(diffs)
                return "commit message"

            coder.repo.get_commit_message = MagicMock(side_effect=mock_get_commit_message)
            coder.send = mock_send

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
            coder = Coder.create(self.GPT35, "diff", io=io, fnames=[str(fname)])

            def mock_send(*args, **kwargs):
                coder.partial_response_content = f"""
Do this:

{str(fname)}
<<<<<<< SEARCH
one
=======
two
>>>>>>> REPLACE

"""
                coder.partial_response_function_call = dict()
                return []

            saved_diffs = []

            def mock_get_commit_message(diffs, context, user_language=None):
                saved_diffs.append(diffs)
                return "commit message"

            coder.repo.get_commit_message = MagicMock(side_effect=mock_get_commit_message)
            coder.send = mock_send

            coder.run(with_message="hi")

            content = fname.read_text()
            self.assertEqual(content, "two\n")

            diff = saved_diffs[0]
            self.assertIn("file.txt", diff)

    def test_skip_aiderignored_files(self):
        with GitTemporaryDirectory():
            repo = git.Repo()

            fname1 = "ignoreme1.txt"
            fname2 = "ignoreme2.txt"
            fname3 = "dir/ignoreme3.txt"

            Path(fname2).touch()
            repo.git.add(str(fname2))
            repo.git.commit("-m", "initial")

            io = InputOutput(yes=True)

            fnames = [fname1, fname2, fname3]

            aignore = Path(".aiderignore")
            aignore.write_text(f"{fname1}\n{fname2}\ndir\n")
            repo = GitRepo(
                io,
                fnames,
                None,
                aider_ignore_file=str(aignore),
            )

            coder = Coder.create(
                self.GPT35,
                None,
                io,
                fnames=fnames,
                repo=repo,
            )

            self.assertNotIn(fname1, str(coder.abs_fnames))
            self.assertNotIn(fname2, str(coder.abs_fnames))
            self.assertNotIn(fname3, str(coder.abs_fnames))

    def test_skip_gitignored_files_on_init(self):
        with GitTemporaryDirectory() as _:
            repo_path = Path(".")
            repo = git.Repo.init(repo_path)

            ignored_file = repo_path / "ignored_by_git.txt"
            ignored_file.write_text("This file should be ignored by git.")

            regular_file = repo_path / "regular_file.txt"
            regular_file.write_text("This is a regular file.")

            gitignore_content = "ignored_by_git.txt\n"
            (repo_path / ".gitignore").write_text(gitignore_content)

            repo.index.add([str(regular_file), ".gitignore"])
            repo.index.commit("Initial commit with gitignore and regular file")

            mock_io = MagicMock()
            mock_io.tool_warning = MagicMock()

            fnames_to_add = [str(ignored_file), str(regular_file)]

            coder = Coder.create(self.GPT35, None, mock_io, fnames=fnames_to_add)

            self.assertNotIn(str(ignored_file.resolve()), coder.abs_fnames)
            self.assertIn(str(regular_file.resolve()), coder.abs_fnames)
            mock_io.tool_warning.assert_any_call(
                f"Skipping {ignored_file.name} that matches gitignore spec."
            )

    def test_check_for_urls(self):
        io = InputOutput(yes=True)
        coder = Coder.create(self.GPT35, None, io=io)
        coder.commands.scraper = MagicMock()
        coder.commands.scraper.scrape = MagicMock(return_value="some content")

        # Test various URL formats
        test_cases = [
            ("Check http://example.com, it's cool", "http://example.com"),
            (
                "Visit https://www.example.com/page and see stuff",
                "https://www.example.com/page",
            ),
            (
                "Go to http://subdomain.example.com:8080/path?query=value, or not",
                "http://subdomain.example.com:8080/path?query=value",
            ),
            (
                "See https://example.com/path#fragment for example",
                "https://example.com/path#fragment",
            ),
            ("Look at http://localhost:3000", "http://localhost:3000"),
            (
                "View https://example.com/setup#whatever",
                "https://example.com/setup#whatever",
            ),
            ("Open http://127.0.0.1:8000/api/v1/", "http://127.0.0.1:8000/api/v1/"),
            (
                "Try https://example.com/path/to/page.html?param1=value1&param2=value2",
                "https://example.com/path/to/page.html?param1=value1&param2=value2",
            ),
            (
                "Access http://user:password@example.com",
                "http://user:password@example.com",
            ),
            (
                "Use https://example.com/path_(with_parentheses)",
                "https://example.com/path_(with_parentheses)",
            ),
        ]

        for input_text, expected_url in test_cases:
            with self.subTest(input_text=input_text):
                result = coder.check_for_urls(input_text)
                self.assertIn(expected_url, result)

        # Test cases from the GitHub issue
        issue_cases = [
            ("check http://localhost:3002, there is an error", "http://localhost:3002"),
            (
                "can you check out https://example.com/setup#whatever",
                "https://example.com/setup#whatever",
            ),
        ]

        for input_text, expected_url in issue_cases:
            with self.subTest(input_text=input_text):
                result = coder.check_for_urls(input_text)
                self.assertIn(expected_url, result)

        # Test case with multiple URLs
        multi_url_input = "Check http://example1.com and https://example2.com/page"
        result = coder.check_for_urls(multi_url_input)
        self.assertIn("http://example1.com", result)
        self.assertIn("https://example2.com/page", result)

        # Test case with no URL
        no_url_input = "This text contains no URL"
        result = coder.check_for_urls(no_url_input)
        self.assertEqual(result, no_url_input)

        # Test case with the same URL appearing multiple times
        repeated_url_input = (
            "Check https://example.com, then https://example.com again, and https://example.com one"
            " more time"
        )
        result = coder.check_for_urls(repeated_url_input)
        # the original 3 in the input text, plus 1 more for the scraped text
        self.assertEqual(result.count("https://example.com"), 4)
        self.assertIn("https://example.com", result)

    def test_coder_from_coder_with_subdir(self):
        with GitTemporaryDirectory() as root:
            repo = git.Repo.init(root)

            # Create a file in a subdirectory
            subdir = Path(root) / "subdir"
            subdir.mkdir()
            test_file = subdir / "test_file.txt"
            test_file.write_text("Test content")

            repo.git.add(str(test_file))
            repo.git.commit("-m", "Add test file")

            # Change directory to the subdirectory
            os.chdir(subdir.resolve())

            # Create the first coder
            io = InputOutput(yes=True)
            coder1 = Coder.create(self.GPT35, None, io=io, fnames=[test_file.name])

            # Create a new coder from the first coder
            coder2 = Coder.create(from_coder=coder1)

            # Check if both coders have the same set of abs_fnames
            self.assertEqual(coder1.abs_fnames, coder2.abs_fnames)

            # Ensure the abs_fnames contain the correct absolute path
            expected_abs_path = os.path.realpath(str(test_file))
            coder1_abs_fnames = set(os.path.realpath(path) for path in coder1.abs_fnames)
            self.assertIn(expected_abs_path, coder1_abs_fnames)
            self.assertIn(expected_abs_path, coder2.abs_fnames)

            # Check that the abs_fnames do not contain duplicate or incorrect paths
            self.assertEqual(len(coder1.abs_fnames), 1)
            self.assertEqual(len(coder2.abs_fnames), 1)

    def test_suggest_shell_commands(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            def mock_send(*args, **kwargs):
                coder.partial_response_content = """Here's a shell command to run:

```bash
echo "Hello, World!"
```

This command will print 'Hello, World!' to the console."""
                coder.partial_response_function_call = dict()
                return []

            coder.send = mock_send

            # Mock the handle_shell_commands method to check if it's called
            coder.handle_shell_commands = MagicMock()

            # Run the coder with a message
            coder.run(with_message="Suggest a shell command")

            # Check if the shell command was added to the list
            self.assertEqual(len(coder.shell_commands), 1)
            self.assertEqual(coder.shell_commands[0].strip(), 'echo "Hello, World!"')

            # Check if handle_shell_commands was called with the correct argument
            coder.handle_shell_commands.assert_called_once()

    def test_no_suggest_shell_commands(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io, suggest_shell_commands=False)
            self.assertFalse(coder.suggest_shell_commands)

    def test_detect_urls_enabled(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io, detect_urls=True)
            coder.commands.scraper = MagicMock()
            coder.commands.scraper.scrape = MagicMock(return_value="some content")

            # Test with a message containing a URL
            message = "Check out https://example.com"
            coder.check_for_urls(message)
            coder.commands.scraper.scrape.assert_called_once_with("https://example.com")

    def test_detect_urls_disabled(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io, detect_urls=False)
            coder.commands.scraper = MagicMock()
            coder.commands.scraper.scrape = MagicMock(return_value="some content")

            # Test with a message containing a URL
            message = "Check out https://example.com"
            result = coder.check_for_urls(message)
            self.assertEqual(result, message)
            coder.commands.scraper.scrape.assert_not_called()

    def test_unknown_edit_format_exception(self):
        # Test the exception message format
        invalid_format = "invalid_format"
        valid_formats = ["diff", "whole", "map"]
        exc = UnknownEditFormat(invalid_format, valid_formats)
        expected_msg = (
            f"Unknown edit format {invalid_format}. Valid formats are: {', '.join(valid_formats)}"
        )
        self.assertEqual(str(exc), expected_msg)

    def test_unknown_edit_format_creation(self):
        # Test that creating a Coder with invalid edit format raises the exception
        io = InputOutput(yes=True)
        invalid_format = "invalid_format"

        with self.assertRaises(UnknownEditFormat) as cm:
            Coder.create(self.GPT35, invalid_format, io=io)

        exc = cm.exception
        self.assertEqual(exc.edit_format, invalid_format)
        self.assertIsInstance(exc.valid_formats, list)
        self.assertTrue(len(exc.valid_formats) > 0)

    def test_system_prompt_prefix(self):
        # Test that system_prompt_prefix is properly set and used
        io = InputOutput(yes=True)
        test_prefix = "Test prefix. "

        # Create a model with system_prompt_prefix
        model = Model("gpt-3.5-turbo")
        model.system_prompt_prefix = test_prefix

        coder = Coder.create(model, None, io=io)

        # Get the formatted messages
        chunks = coder.format_messages()
        messages = chunks.all_messages()

        # Check if the system message contains our prefix
        system_message = next(msg for msg in messages if msg["role"] == "system")
        self.assertTrue(system_message["content"].startswith(test_prefix))

    def test_coder_create_with_new_file_oserror(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            new_file = "new_file.txt"

            # Mock Path.touch() to raise OSError
            with patch("pathlib.Path.touch", side_effect=OSError("Permission denied")):
                # Create the coder with a new file
                coder = Coder.create(self.GPT35, "diff", io=io, fnames=[new_file])

            # Check if the coder was created successfully
            self.assertIsInstance(coder, Coder)

            # Check if the new file is not in abs_fnames
            self.assertNotIn(new_file, [os.path.basename(f) for f in coder.abs_fnames])

    def test_show_exhausted_error(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            # Set up some real done_messages and cur_messages
            coder.done_messages = [
                {
                    "role": "user",
                    "content": "Hello, can you help me with a Python problem?",
                },
                {
                    "role": "assistant",
                    "content": "Of course! I'd be happy to help. What's the problem you're facing?",
                },
                {
                    "role": "user",
                    "content": (
                        "I need to write a function that calculates the factorial of a number."
                    ),
                },
                {
                    "role": "assistant",
                    "content": (
                        "Sure, I can help you with that. Here's a simple Python function to"
                        " calculate the factorial of a number:"
                    ),
                },
            ]

            coder.cur_messages = [
                {
                    "role": "user",
                    "content": "Can you optimize this function for large numbers?",
                },
            ]

            # Set up real values for the main model
            coder.main_model.info = {
                "max_input_tokens": 4000,
                "max_output_tokens": 1000,
            }
            coder.partial_response_content = (
                "Here's an optimized version of the factorial function:"
            )
            coder.io.tool_error = MagicMock()

            # Call the method
            coder.show_exhausted_error()

            # Check if tool_error was called with the expected message
            coder.io.tool_error.assert_called()
            error_message = coder.io.tool_error.call_args[0][0]

            # Assert that the error message contains the expected information
            self.assertIn("Model gpt-3.5-turbo has hit a token limit!", error_message)
            self.assertIn("Input tokens:", error_message)
            self.assertIn("Output tokens:", error_message)
            self.assertIn("Total tokens:", error_message)

    def test_keyboard_interrupt_handling(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            # Simulate keyboard interrupt during message processing
            def mock_send(*args, **kwargs):
                coder.partial_response_content = "Partial response"
                coder.partial_response_function_call = dict()
                raise KeyboardInterrupt()

            coder.send = mock_send

            # Initial valid state
            sanity_check_messages(coder.cur_messages)

            # Process message that will trigger interrupt
            list(coder.send_message("Test message"))

            # Verify messages are still in valid state
            sanity_check_messages(coder.cur_messages)
            self.assertEqual(coder.cur_messages[-1]["role"], "assistant")

    def test_token_limit_error_handling(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            # Simulate token limit error
            def mock_send(*args, **kwargs):
                coder.partial_response_content = "Partial response"
                coder.partial_response_function_call = dict()
                raise FinishReasonLength()

            coder.send = mock_send

            # Initial valid state
            sanity_check_messages(coder.cur_messages)

            # Process message that hits token limit
            list(coder.send_message("Long message"))

            # Verify messages are still in valid state
            sanity_check_messages(coder.cur_messages)
            self.assertEqual(coder.cur_messages[-1]["role"], "assistant")

    def test_message_sanity_after_partial_response(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            # Simulate partial response then interrupt
            def mock_send(*args, **kwargs):
                coder.partial_response_content = "Partial response"
                coder.partial_response_function_call = dict()
                raise KeyboardInterrupt()

            coder.send = mock_send

            list(coder.send_message("Test"))

            # Verify message structure remains valid
            sanity_check_messages(coder.cur_messages)
            self.assertEqual(coder.cur_messages[-1]["role"], "assistant")

    def test_normalize_language(self):
        coder = Coder.create(self.GPT35, None, io=InputOutput())

        # Test None and empty
        self.assertIsNone(coder.normalize_language(None))
        self.assertIsNone(coder.normalize_language(""))

        # Test "C" and "POSIX"
        self.assertIsNone(coder.normalize_language("C"))
        self.assertIsNone(coder.normalize_language("POSIX"))

        # Test already formatted names
        self.assertEqual(coder.normalize_language("English"), "English")
        self.assertEqual(coder.normalize_language("French"), "French")

        # Test common locale codes (fallback map, assuming babel is not installed or fails)
        with patch("aider.coders.base_coder.Locale", None):
            self.assertEqual(coder.normalize_language("en_US"), "English")
            self.assertEqual(coder.normalize_language("fr_FR"), "French")
            self.assertEqual(coder.normalize_language("es"), "Spanish")
            self.assertEqual(coder.normalize_language("de_DE.UTF-8"), "German")
            self.assertEqual(
                coder.normalize_language("zh-CN"), "Chinese"
            )  # Test hyphen in fallback
            self.assertEqual(coder.normalize_language("ja"), "Japanese")
            self.assertEqual(
                coder.normalize_language("unknown_code"), "unknown_code"
            )  # Fallback to original

        # Test with babel.Locale mocked (available)
        mock_babel_locale = MagicMock()
        mock_locale_instance = MagicMock()
        mock_babel_locale.parse.return_value = mock_locale_instance

        with patch("aider.coders.base_coder.Locale", mock_babel_locale):
            mock_locale_instance.get_display_name.return_value = "english"  # For en_US
            self.assertEqual(coder.normalize_language("en_US"), "English")
            mock_babel_locale.parse.assert_called_with("en_US")
            mock_locale_instance.get_display_name.assert_called_with("en")

            mock_locale_instance.get_display_name.return_value = "french"  # For fr-FR
            self.assertEqual(coder.normalize_language("fr-FR"), "French")  # Test with hyphen
            mock_babel_locale.parse.assert_called_with("fr_FR")  # Hyphen replaced
            mock_locale_instance.get_display_name.assert_called_with("en")

        # Test with babel.Locale raising an exception (simulating parse failure)
        mock_babel_locale_error = MagicMock()
        mock_babel_locale_error.parse.side_effect = Exception("Babel parse error")
        with patch("aider.coders.base_coder.Locale", mock_babel_locale_error):
            self.assertEqual(coder.normalize_language("en_US"), "English")  # Falls back to map

    def test_get_user_language(self):
        io = InputOutput()
        coder = Coder.create(self.GPT35, None, io=io)

        # 1. Test with self.chat_language set
        coder.chat_language = "fr_CA"
        with patch.object(coder, "normalize_language", return_value="French Canadian") as mock_norm:
            self.assertEqual(coder.get_user_language(), "French Canadian")
            mock_norm.assert_called_once_with("fr_CA")
        coder.chat_language = None  # Reset

        # 2. Test with locale.getlocale()
        with patch("locale.getlocale", return_value=("en_GB", "UTF-8")) as mock_getlocale:
            with patch.object(
                coder, "normalize_language", return_value="British English"
            ) as mock_norm:
                self.assertEqual(coder.get_user_language(), "British English")
                mock_getlocale.assert_called_once()
                mock_norm.assert_called_once_with("en_GB")

        # Test with locale.getlocale() returning None or empty
        with patch("locale.getlocale", return_value=(None, None)) as mock_getlocale:
            with patch("os.environ.get") as mock_env_get:  # Ensure env vars are not used yet
                mock_env_get.return_value = None
                # Should be None if nothing found
                self.assertIsNone(coder.get_user_language())

        # 3. Test with environment variables: LANG
        with patch(
            "locale.getlocale", side_effect=Exception("locale error")
        ):  # Mock locale to fail
            with patch("os.environ.get") as mock_env_get:
                mock_env_get.side_effect = lambda key: "de_DE.UTF-8" if key == "LANG" else None
                with patch.object(coder, "normalize_language", return_value="German") as mock_norm:
                    self.assertEqual(coder.get_user_language(), "German")
                    mock_env_get.assert_any_call("LANG")
                    mock_norm.assert_called_once_with("de_DE")

        # Test LANGUAGE (takes precedence over LANG if both were hypothetically checked
        # by os.environ.get, but our code checks in order, so we mock the first one it finds)
        with patch("locale.getlocale", side_effect=Exception("locale error")):
            with patch("os.environ.get") as mock_env_get:
                mock_env_get.side_effect = lambda key: "es_ES" if key == "LANGUAGE" else None
                with patch.object(coder, "normalize_language", return_value="Spanish") as mock_norm:
                    self.assertEqual(coder.get_user_language(), "Spanish")
                    # LANG would be called first
                    mock_env_get.assert_any_call("LANGUAGE")
                    mock_norm.assert_called_once_with("es_ES")

        # 4. Test priority: chat_language > locale > env
        coder.chat_language = "it_IT"
        with patch("locale.getlocale", return_value=("en_US", "UTF-8")) as mock_getlocale:
            with patch("os.environ.get", return_value="de_DE") as mock_env_get:
                with patch.object(
                    coder, "normalize_language", side_effect=lambda x: x.upper()
                ) as mock_norm:
                    self.assertEqual(coder.get_user_language(), "IT_IT")  # From chat_language
                    mock_norm.assert_called_once_with("it_IT")
                    mock_getlocale.assert_not_called()
                    mock_env_get.assert_not_called()
        coder.chat_language = None

        # 5. Test when no language is found
        with patch("locale.getlocale", side_effect=Exception("locale error")):
            with patch("os.environ.get", return_value=None) as mock_env_get:
                self.assertIsNone(coder.get_user_language())

    def test_architect_coder_auto_accept_true(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            io.confirm_ask = MagicMock(return_value=True)

            # Create an ArchitectCoder with auto_accept_architect=True
            with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
                from aider.coders.architect_coder import ArchitectCoder

                coder = ArchitectCoder()
                coder.io = io
                coder.main_model = self.GPT35
                coder.auto_accept_architect = True
                coder.verbose = False
                coder.total_cost = 0
                coder.cur_messages = []
                coder.done_messages = []
                coder.summarizer = MagicMock()
                coder.summarizer.too_big.return_value = False

                # Mock editor_coder creation and execution
                mock_editor = MagicMock()
                with patch(
                    "aider.coders.architect_coder.Coder.create",
                    return_value=mock_editor,
                ):
                    # Set partial response content
                    coder.partial_response_content = "Make these changes to the code"

                    # Call reply_completed
                    coder.reply_completed()

                    # Verify that confirm_ask was not called (auto-accepted)
                    io.confirm_ask.assert_not_called()

                    # Verify that editor coder was created and run
                    mock_editor.run.assert_called_once()

    def test_architect_coder_auto_accept_false_confirmed(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=False)
            io.confirm_ask = MagicMock(return_value=True)

            # Create an ArchitectCoder with auto_accept_architect=False
            with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
                from aider.coders.architect_coder import ArchitectCoder

                coder = ArchitectCoder()
                coder.io = io
                coder.main_model = self.GPT35
                coder.auto_accept_architect = False
                coder.verbose = False
                coder.total_cost = 0
                coder.cur_messages = []
                coder.done_messages = []
                coder.summarizer = MagicMock()
                coder.summarizer.too_big.return_value = False
                coder.cur_messages = []
                coder.done_messages = []
                coder.summarizer = MagicMock()
                coder.summarizer.too_big.return_value = False

                # Mock editor_coder creation and execution
                mock_editor = MagicMock()
                with patch(
                    "aider.coders.architect_coder.Coder.create",
                    return_value=mock_editor,
                ):
                    # Set partial response content
                    coder.partial_response_content = "Make these changes to the code"

                    # Call reply_completed
                    coder.reply_completed()

                    # Verify that confirm_ask was called
                    io.confirm_ask.assert_called_once_with("Edit the files?")

                    # Verify that editor coder was created and run
                    mock_editor.run.assert_called_once()

    def test_architect_coder_auto_accept_false_rejected(self):
        with GitTemporaryDirectory():
            io = InputOutput(yes=False)
            io.confirm_ask = MagicMock(return_value=False)

            # Create an ArchitectCoder with auto_accept_architect=False
            with patch("aider.coders.architect_coder.AskCoder.__init__", return_value=None):
                from aider.coders.architect_coder import ArchitectCoder

                coder = ArchitectCoder()
                coder.io = io
                coder.main_model = self.GPT35
                coder.auto_accept_architect = False
                coder.verbose = False
                coder.total_cost = 0

                # Mock editor_coder creation and execution
                mock_editor = MagicMock()
                with patch(
                    "aider.coders.architect_coder.Coder.create",
                    return_value=mock_editor,
                ):
                    # Set partial response content
                    coder.partial_response_content = "Make these changes to the code"

                    # Call reply_completed
                    coder.reply_completed()

                    # Verify that confirm_ask was called
                    io.confirm_ask.assert_called_once_with("Edit the files?")

                    # Verify that editor coder was NOT created or run
                    # (because user rejected the changes)
                    mock_editor.run.assert_not_called()

    @patch("aider.coders.base_coder.experimental_mcp_client")
    def test_mcp_server_connection(self, mock_mcp_client):
        """Test that the coder connects to MCP servers for tools."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)

            # Create mock MCP server
            mock_server = MagicMock()
            mock_server.name = "test_server"
            mock_server.connect = MagicMock()
            mock_server.disconnect = MagicMock()

            # Setup mock for initialize_mcp_tools
            mock_tools = [("test_server", [{"function": {"name": "test_tool"}}])]

            # Create coder with mock MCP server
            with patch.object(Coder, "initialize_mcp_tools", return_value=mock_tools):
                coder = Coder.create(self.GPT35, "diff", io=io, mcp_servers=[mock_server])

                # Manually set mcp_tools since we're bypassing initialize_mcp_tools
                coder.mcp_tools = mock_tools

                # Verify that mcp_tools contains the expected data
                self.assertIsNotNone(coder.mcp_tools)
                self.assertEqual(len(coder.mcp_tools), 1)
                self.assertEqual(coder.mcp_tools[0][0], "test_server")

    @patch("aider.coders.base_coder.experimental_mcp_client")
    def test_coder_creation_with_partial_failed_mcp_server(self, mock_mcp_client):
        """Test that a coder can still be created even if an MCP server fails to initialize."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            io.tool_warning = MagicMock()

            # Create mock MCP servers - one working, one failing
            working_server = AsyncMock()
            working_server.name = "working_server"
            working_server.connect = AsyncMock()
            working_server.disconnect = AsyncMock()

            failing_server = AsyncMock()
            failing_server.name = "failing_server"
            failing_server.connect = AsyncMock()
            failing_server.disconnect = AsyncMock()

            # Mock load_mcp_tools to succeed for working_server and fail for failing_server
            async def mock_load_mcp_tools(session, format):
                if session == await working_server.connect():
                    return [{"function": {"name": "working_tool"}}]
                else:
                    raise Exception("Failed to load tools")

            mock_mcp_client.load_mcp_tools = AsyncMock(side_effect=mock_load_mcp_tools)

            # Create coder with both servers
            coder = Coder.create(
                self.GPT35,
                "diff",
                io=io,
                mcp_servers=[working_server, failing_server],
                verbose=True,
            )

            # Verify that coder was created successfully
            self.assertIsInstance(coder, Coder)

            # Verify that only the working server's tools were added
            self.assertIsNotNone(coder.mcp_tools)
            self.assertEqual(len(coder.mcp_tools), 1)
            self.assertEqual(coder.mcp_tools[0][0], "working_server")

            # Verify that the tool list contains only working tools
            tool_list = coder.get_tool_list()
            self.assertEqual(len(tool_list), 1)
            self.assertEqual(tool_list[0]["function"]["name"], "working_tool")

            # Verify that the warning was logged for the failing server
            io.tool_warning.assert_called_with(
                "Error initializing MCP server failing_server:\nFailed to load tools"
            )

    @patch("aider.coders.base_coder.experimental_mcp_client")
    def test_coder_creation_with_all_failed_mcp_server(self, mock_mcp_client):
        """Test that a coder can still be created even if an MCP server fails to initialize."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            io.tool_warning = MagicMock()

            failing_server = AsyncMock()
            failing_server.name = "failing_server"
            failing_server.connect = AsyncMock()
            failing_server.disconnect = AsyncMock()

            # Mock load_mcp_tools to succeed for working_server and fail for failing_server
            async def mock_load_mcp_tools(session, format):
                raise Exception("Failed to load tools")

            mock_mcp_client.load_mcp_tools = AsyncMock(side_effect=mock_load_mcp_tools)

            # Create coder with both servers
            coder = Coder.create(
                self.GPT35,
                "diff",
                io=io,
                mcp_servers=[failing_server],
                verbose=True,
            )

            # Verify that coder was created successfully
            self.assertIsInstance(coder, Coder)

            # Verify that only the working server's tools were added
            self.assertIsNotNone(coder.mcp_tools)
            self.assertEqual(len(coder.mcp_tools), 0)

            # Verify that the tool list contains only working tools
            tool_list = coder.get_tool_list()
            self.assertEqual(len(tool_list), 0)

            # Verify that the warning was logged for the failing server
            io.tool_warning.assert_called_with(
                "Error initializing MCP server failing_server:\nFailed to load tools"
            )

    def test_process_tool_calls_none_response(self):
        """Test that process_tool_calls handles None response correctly."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            # Test with None response
            result = coder.process_tool_calls(None)
            self.assertFalse(result)

    def test_process_tool_calls_no_tool_calls(self):
        """Test that process_tool_calls handles response with no tool calls."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            # Create a response with no tool calls
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message = MagicMock()
            response.choices[0].message.tool_calls = []

            result = coder.process_tool_calls(response)
            self.assertFalse(result)

    @patch("aider.coders.base_coder.experimental_mcp_client")
    @patch("asyncio.run")
    def test_process_tool_calls_with_tools(self, mock_asyncio_run, mock_mcp_client):
        """Test that process_tool_calls processes tool calls correctly."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            io.confirm_ask = MagicMock(return_value=True)

            # Create mock MCP server
            mock_server = MagicMock()
            mock_server.name = "test_server"

            # Create a tool call
            tool_call = MagicMock()
            tool_call.id = "test_id"
            tool_call.type = "function"
            tool_call.function = MagicMock()
            tool_call.function.name = "test_tool"
            tool_call.function.arguments = '{"param": "value"}'

            # Create a response with tool calls
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message = MagicMock()
            response.choices[0].message.tool_calls = [tool_call]
            response.choices[0].message.to_dict = MagicMock(
                return_value={"role": "assistant", "tool_calls": [{"id": "test_id"}]}
            )

            # Create coder with mock MCP tools and servers
            coder = Coder.create(self.GPT35, "diff", io=io)
            coder.mcp_tools = [("test_server", [{"function": {"name": "test_tool"}}])]
            coder.mcp_servers = [mock_server]

            # Mock asyncio.run to return tool responses
            tool_responses = [
                [
                    {
                        "role": "tool",
                        "tool_call_id": "test_id",
                        "content": "Tool execution result",
                    }
                ]
            ]
            mock_asyncio_run.return_value = tool_responses

            # Test process_tool_calls
            result = coder.process_tool_calls(response)
            self.assertTrue(result)

            # Verify that asyncio.run was called
            mock_asyncio_run.assert_called_once()

            # Verify that the messages were added
            self.assertEqual(len(coder.cur_messages), 2)
            self.assertEqual(coder.cur_messages[0]["role"], "assistant")
            self.assertEqual(coder.cur_messages[1]["role"], "tool")
            self.assertEqual(coder.cur_messages[1]["tool_call_id"], "test_id")
            self.assertEqual(coder.cur_messages[1]["content"], "Tool execution result")

    def test_process_tool_calls_max_calls_exceeded(self):
        """Test that process_tool_calls handles max tool calls exceeded."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            io.tool_warning = MagicMock()

            # Create a tool call
            tool_call = MagicMock()
            tool_call.id = "test_id"
            tool_call.type = "function"
            tool_call.function = MagicMock()
            tool_call.function.name = "test_tool"

            # Create a response with tool calls
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message = MagicMock()
            response.choices[0].message.tool_calls = [tool_call]

            # Create mock MCP server
            mock_server = MagicMock()
            mock_server.name = "test_server"

            # Create coder with max tool calls exceeded
            coder = Coder.create(self.GPT35, "diff", io=io)
            coder.num_tool_calls = coder.max_tool_calls
            coder.mcp_tools = [("test_server", [{"function": {"name": "test_tool"}}])]
            coder.mcp_servers = [mock_server]

            # Test process_tool_calls
            result = coder.process_tool_calls(response)
            self.assertFalse(result)

            # Verify that warning was shown
            io.tool_warning.assert_called_once_with(
                f"Only {coder.max_tool_calls} tool calls allowed, stopping."
            )

    def test_process_tool_calls_user_rejects(self):
        """Test that process_tool_calls handles user rejection."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            io.confirm_ask = MagicMock(return_value=False)

            # Create a tool call
            tool_call = MagicMock()
            tool_call.id = "test_id"
            tool_call.type = "function"
            tool_call.function = MagicMock()
            tool_call.function.name = "test_tool"

            # Create a response with tool calls
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message = MagicMock()
            response.choices[0].message.tool_calls = [tool_call]

            # Create mock MCP server
            mock_server = MagicMock()
            mock_server.name = "test_server"

            # Create coder with mock MCP tools
            coder = Coder.create(self.GPT35, "diff", io=io)
            coder.mcp_tools = [("test_server", [{"function": {"name": "test_tool"}}])]
            coder.mcp_servers = [mock_server]

            # Test process_tool_calls
            result = coder.process_tool_calls(response)
            self.assertFalse(result)

            # Verify that confirm_ask was called
            io.confirm_ask.assert_called_once_with("Run tools?")

            # Verify that no messages were added
            self.assertEqual(len(coder.cur_messages), 0)

    @patch("asyncio.run")
    def test_execute_tool_calls(self, mock_asyncio_run):
        """Test that _execute_tool_calls executes tool calls correctly."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            # Create mock server and tool call
            mock_server = MagicMock()
            mock_server.name = "test_server"

            tool_call = MagicMock()
            tool_call.id = "test_id"
            tool_call.type = "function"
            tool_call.function = MagicMock()
            tool_call.function.name = "test_tool"
            tool_call.function.arguments = '{"param": "value"}'

            # Create server_tool_calls
            server_tool_calls = {mock_server: [tool_call]}

            # Mock asyncio.run to return tool responses
            tool_responses = [
                [
                    {
                        "role": "tool",
                        "tool_call_id": "test_id",
                        "content": "Tool execution result",
                    }
                ]
            ]
            mock_asyncio_run.return_value = tool_responses

            # Test _execute_tool_calls directly
            result = coder._execute_tool_calls(server_tool_calls)

            # Verify that asyncio.run was called
            mock_asyncio_run.assert_called_once()

            # Verify that the correct tool responses were returned
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["role"], "tool")
            self.assertEqual(result[0]["tool_call_id"], "test_id")
            self.assertEqual(result[0]["content"], "Tool execution result")

    def test_auto_commit_with_none_content_message(self):
        """
        Verify that auto_commit works with messages that have None content.
        This is common with tool calls.
        """
        with GitTemporaryDirectory():
            repo = git.Repo()

            fname = Path("file1.txt")
            fname.write_text("one\n")
            repo.git.add(str(fname))
            repo.git.commit("-m", "initial")

            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io, fnames=[str(fname)])

            coder.cur_messages = [
                {"role": "user", "content": "do a thing"},
                {"role": "assistant", "content": None},
            ]

            # The context for commit message will be generated from cur_messages.
            # This call should not raise an exception due to `content: None`.

            def mock_get_commit_message(diffs, context, user_language=None):
                self.assertIn("USER: do a thing", context)
                # None becomes empty string.
                self.assertIn("ASSISTANT: \n", context)
                return "commit message"

            coder.repo.get_commit_message = MagicMock(side_effect=mock_get_commit_message)

            # To trigger a commit, the file must be modified
            fname.write_text("one changed\n")

            res = coder.auto_commit({str(fname)})
            self.assertIsNotNone(res)

            # A new commit should be created
            num_commits = len(list(repo.iter_commits()))
            self.assertEqual(num_commits, 2)

            coder.repo.get_commit_message.assert_called_once()

    @patch(
        "aider.coders.base_coder.experimental_mcp_client.call_openai_tool",
        new_callable=AsyncMock,
    )
    def test_execute_tool_calls_multiple_content(self, mock_call_openai_tool):
        """Test that _execute_tool_calls handles multiple content blocks correctly."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            # Create mock server and tool call
            mock_server = AsyncMock()
            mock_server.name = "test_server"

            tool_call = MagicMock()
            tool_call.id = "test_id"
            tool_call.type = "function"
            tool_call.function = MagicMock()
            tool_call.function.name = "test_tool"
            tool_call.function.arguments = '{"param": "value"}'

            # Create server_tool_calls
            server_tool_calls = {mock_server: [tool_call]}

            # Mock the return value of call_openai_tool
            mock_content1 = MagicMock(spec=["text"])
            mock_content1.text = "First part. "
            mock_content2 = MagicMock(spec=["text"])
            mock_content2.text = "Second part."

            mock_call_result = MagicMock()
            mock_call_result.content = [mock_content1, mock_content2]
            mock_call_openai_tool.return_value = mock_call_result

            # Test _execute_tool_calls directly
            result = coder._execute_tool_calls(server_tool_calls)

            # Verify that call_openai_tool was called
            mock_call_openai_tool.assert_called_once()

            # Verify that the correct tool responses were returned
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["role"], "tool")
            self.assertEqual(result[0]["tool_call_id"], "test_id")
            # This will fail with the current code, which is the point of the test.
            # The current code returns a hardcoded string.
            # A fixed version should concatenate the text from all content blocks.
            self.assertEqual(result[0]["content"], "First part. Second part.")

    @patch(
        "aider.coders.base_coder.experimental_mcp_client.call_openai_tool",
        new_callable=AsyncMock,
    )
    def test_execute_tool_calls_blob_content(self, mock_call_openai_tool):
        """Test that _execute_tool_calls handles BlobResourceContents correctly."""
        with GitTemporaryDirectory():
            io = InputOutput(yes=True)
            coder = Coder.create(self.GPT35, "diff", io=io)

            # Create mock server and tool call
            mock_server = AsyncMock()
            mock_server.name = "test_server"

            tool_call = MagicMock()
            tool_call.id = "test_id"
            tool_call.type = "function"
            tool_call.function = MagicMock()
            tool_call.function.name = "test_tool"
            tool_call.function.arguments = '{"param": "value"}'

            # Create server_tool_calls
            server_tool_calls = {mock_server: [tool_call]}

            # Mock BlobResourceContents for text
            text_blob_content = "Hello from blob! "
            encoded_text_blob = base64.b64encode(text_blob_content.encode("utf-8")).decode("utf-8")
            mock_text_blob_resource = MagicMock(spec=["blob"])
            mock_text_blob_resource.blob = encoded_text_blob

            mock_embedded_text_resource = MagicMock(spec=["resource"])
            mock_embedded_text_resource.resource = mock_text_blob_resource

            # Mock BlobResourceContents for binary data
            binary_blob_content = b"\x80\x81\x82"
            encoded_binary_blob = base64.b64encode(binary_blob_content).decode("utf-8")
            mock_binary_blob_resource = MagicMock(spec=["blob", "name", "mimeType"])
            mock_binary_blob_resource.blob = encoded_binary_blob
            mock_binary_blob_resource.name = "binary.dat"
            mock_binary_blob_resource.mimeType = "application/octet-stream"

            mock_embedded_binary_resource = MagicMock(spec=["resource"])
            mock_embedded_binary_resource.resource = mock_binary_blob_resource

            # Mock TextContent
            mock_text_content = MagicMock(spec=["text"])
            mock_text_content.text = "Plain text. "

            mock_call_result = MagicMock()
            mock_call_result.content = [
                mock_text_content,
                mock_embedded_text_resource,
                mock_embedded_binary_resource,
            ]
            mock_call_openai_tool.return_value = mock_call_result

            # Test _execute_tool_calls directly
            result = coder._execute_tool_calls(server_tool_calls)

            # Verify that call_openai_tool was called
            mock_call_openai_tool.assert_called_once()

            # Verify that the correct tool responses were returned
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["role"], "tool")
            self.assertEqual(result[0]["tool_call_id"], "test_id")

            expected_content = (
                "Plain text. Hello from blob! [embedded binary resource: binary.dat"
                " (application/octet-stream)]"
            )
            self.assertEqual(result[0]["content"], expected_content)


if __name__ == "__main__":
    unittest.main()
