import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import git

from aider.coders import Coder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo
from aider.utils import GitTemporaryDirectory


class TestCoder(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")

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

            def mock_get_commit_message(diffs, context):
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

            def mock_get_commit_message(diffs, context):
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

            def mock_get_commit_message(diffs, context):
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

    def test_check_for_urls(self):
        io = InputOutput(yes=True)
        coder = Coder.create(self.GPT35, None, io=io)
        coder.commands.scraper = MagicMock()
        coder.commands.scraper.scrape = MagicMock(return_value="some content")

        # Test various URL formats
        test_cases = [
            ("Check http://example.com, it's cool", "http://example.com"),
            ("Visit https://www.example.com/page and see stuff", "https://www.example.com/page"),
            (
                "Go to http://subdomain.example.com:8080/path?query=value, or not",
                "http://subdomain.example.com:8080/path?query=value",
            ),
            (
                "See https://example.com/path#fragment for example",
                "https://example.com/path#fragment",
            ),
            ("Look at http://localhost:3000", "http://localhost:3000"),
            ("View https://example.com/setup#whatever", "https://example.com/setup#whatever"),
            ("Open http://127.0.0.1:8000/api/v1/", "http://127.0.0.1:8000/api/v1/"),
            (
                "Try https://example.com/path/to/page.html?param1=value1&param2=value2",
                "https://example.com/path/to/page.html?param1=value1&param2=value2",
            ),
            ("Access http://user:password@example.com", "http://user:password@example.com"),
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
        self.assertEqual(result, [])

        # Test case with the same URL appearing multiple times
        repeated_url_input = (
            "Check https://example.com, then https://example.com again, and https://example.com one"
            " more time"
        )
        result = coder.check_for_urls(repeated_url_input)
        self.assertEqual(result.count("https://example.com"), 1)
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
            coder.handle_shell_commands.assert_not_called()

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
                {"role": "user", "content": "Hello, can you help me with a Python problem?"},
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
                {"role": "user", "content": "Can you optimize this function for large numbers?"},
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


if __name__ == "__main__":
    unittest.main()
