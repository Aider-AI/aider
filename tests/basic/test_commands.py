import codecs
import os
import shutil
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest import TestCase, mock

import git
import pyperclip

from aider.coders import Coder
from aider.commands import Commands, SwitchCoder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo
from aider.utils import ChdirTemporaryDirectory, GitTemporaryDirectory, make_repo


class TestCommands(TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

        self.GPT35 = Model("gpt-3.5-turbo")

    def tearDown(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_cmd_add(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Call the cmd_add method with 'foo.txt' and 'bar.txt' as a single string
        commands.cmd_add("foo.txt bar.txt")

        # Check if both files have been created in the temporary directory
        self.assertTrue(os.path.exists("foo.txt"))
        self.assertTrue(os.path.exists("bar.txt"))

    def test_cmd_copy(self):
        # Initialize InputOutput and Coder instances
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Add some assistant messages to the chat history
        coder.done_messages = [
            {"role": "assistant", "content": "First assistant message"},
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Second assistant message"},
        ]

        # Mock pyperclip.copy and io.tool_output
        with (
            mock.patch("pyperclip.copy") as mock_copy,
            mock.patch.object(io, "tool_output") as mock_tool_output,
        ):
            # Invoke the /copy command
            commands.cmd_copy("")

            # Assert pyperclip.copy was called with the last assistant message
            mock_copy.assert_called_once_with("Second assistant message")

            # Assert that tool_output was called with the expected preview
            expected_preview = (
                "Copied last assistant message to clipboard. Preview: Second assistant message"
            )
            mock_tool_output.assert_any_call(expected_preview)

    def test_cmd_copy_with_cur_messages(self):
        # Initialize InputOutput and Coder instances
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Add messages to done_messages and cur_messages
        coder.done_messages = [
            {"role": "assistant", "content": "First assistant message in done_messages"},
            {"role": "user", "content": "User message in done_messages"},
        ]
        coder.cur_messages = [
            {"role": "assistant", "content": "Latest assistant message in cur_messages"},
        ]

        # Mock pyperclip.copy and io.tool_output
        with (
            mock.patch("pyperclip.copy") as mock_copy,
            mock.patch.object(io, "tool_output") as mock_tool_output,
        ):
            # Invoke the /copy command
            commands.cmd_copy("")

            # Assert pyperclip.copy was called with the last assistant message in cur_messages
            mock_copy.assert_called_once_with("Latest assistant message in cur_messages")

            # Assert that tool_output was called with the expected preview
            expected_preview = (
                "Copied last assistant message to clipboard. Preview: Latest assistant message in"
                " cur_messages"
            )
            mock_tool_output.assert_any_call(expected_preview)
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Add only user messages
        coder.done_messages = [
            {"role": "user", "content": "User message"},
        ]

        # Mock io.tool_error
        with mock.patch.object(io, "tool_error") as mock_tool_error:
            commands.cmd_copy("")
            # Assert tool_error was called indicating no assistant messages
            mock_tool_error.assert_called_once_with("No assistant messages found to copy.")

    def test_cmd_copy_pyperclip_exception(self):
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        coder.done_messages = [
            {"role": "assistant", "content": "Assistant message"},
        ]

        # Mock pyperclip.copy to raise an exception
        with (
            mock.patch(
                "pyperclip.copy", side_effect=pyperclip.PyperclipException("Clipboard error")
            ),
            mock.patch.object(io, "tool_error") as mock_tool_error,
        ):
            commands.cmd_copy("")

            # Assert that tool_error was called with the clipboard error message
            mock_tool_error.assert_called_once_with("Failed to copy to clipboard: Clipboard error")

    def test_cmd_add_bad_glob(self):
        # https://github.com/Aider-AI/aider/issues/293

        io = InputOutput(pretty=False, fancy_input=False, yes=False)
        from aider.coders import Coder

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        commands.cmd_add("**.txt")

    def test_cmd_add_with_glob_patterns(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Create some test files
        with open("test1.py", "w") as f:
            f.write("print('test1')")
        with open("test2.py", "w") as f:
            f.write("print('test2')")
        with open("test.txt", "w") as f:
            f.write("test")

        # Call the cmd_add method with a glob pattern
        commands.cmd_add("*.py")

        # Check if the Python files have been added to the chat session
        self.assertIn(str(Path("test1.py").resolve()), coder.abs_fnames)
        self.assertIn(str(Path("test2.py").resolve()), coder.abs_fnames)

        # Check if the text file has not been added to the chat session
        self.assertNotIn(str(Path("test.txt").resolve()), coder.abs_fnames)

    def test_cmd_add_no_match(self):
        # yes=False means we will *not* create the file when it is not found
        io = InputOutput(pretty=False, fancy_input=False, yes=False)
        from aider.coders import Coder

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Call the cmd_add method with a non-existent file pattern
        commands.cmd_add("*.nonexistent")

        # Check if no files have been added to the chat session
        self.assertEqual(len(coder.abs_fnames), 0)

    def test_cmd_add_no_match_but_make_it(self):
        # yes=True means we *will* create the file when it is not found
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        fname = Path("[abc].nonexistent")

        # Call the cmd_add method with a non-existent file pattern
        commands.cmd_add(str(fname))

        # Check if no files have been added to the chat session
        self.assertEqual(len(coder.abs_fnames), 1)
        self.assertTrue(fname.exists())

    def test_cmd_add_drop_directory(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, fancy_input=False, yes=False)
        from aider.coders import Coder

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Create a directory and add files to it using pathlib
        Path("test_dir").mkdir()
        Path("test_dir/another_dir").mkdir()
        Path("test_dir/test_file1.txt").write_text("Test file 1")
        Path("test_dir/test_file2.txt").write_text("Test file 2")
        Path("test_dir/another_dir/test_file.txt").write_text("Test file 3")

        # Call the cmd_add method with a directory
        commands.cmd_add("test_dir test_dir/test_file2.txt")

        # Check if the files have been added to the chat session
        self.assertIn(str(Path("test_dir/test_file1.txt").resolve()), coder.abs_fnames)
        self.assertIn(str(Path("test_dir/test_file2.txt").resolve()), coder.abs_fnames)
        self.assertIn(str(Path("test_dir/another_dir/test_file.txt").resolve()), coder.abs_fnames)

        commands.cmd_drop("test_dir/another_dir")
        self.assertIn(str(Path("test_dir/test_file1.txt").resolve()), coder.abs_fnames)
        self.assertIn(str(Path("test_dir/test_file2.txt").resolve()), coder.abs_fnames)
        self.assertNotIn(
            str(Path("test_dir/another_dir/test_file.txt").resolve()), coder.abs_fnames
        )

        # Issue #139 /add problems when cwd != git_root

        # remember the proper abs path to this file
        abs_fname = str(Path("test_dir/another_dir/test_file.txt").resolve())

        # chdir to someplace other than git_root
        Path("side_dir").mkdir()
        os.chdir("side_dir")

        # add it via it's git_root referenced name
        commands.cmd_add("test_dir/another_dir/test_file.txt")

        # it should be there, but was not in v0.10.0
        self.assertIn(abs_fname, coder.abs_fnames)

        # drop it via it's git_root referenced name
        commands.cmd_drop("test_dir/another_dir/test_file.txt")

        # it should be there, but was not in v0.10.0
        self.assertNotIn(abs_fname, coder.abs_fnames)

    def test_cmd_drop_with_glob_patterns(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        subdir = Path("subdir")
        subdir.mkdir()
        (subdir / "subtest1.py").touch()
        (subdir / "subtest2.py").touch()

        Path("test1.py").touch()
        Path("test2.py").touch()

        # Add some files to the chat session
        commands.cmd_add("*.py")

        self.assertEqual(len(coder.abs_fnames), 2)

        # Call the cmd_drop method with a glob pattern
        commands.cmd_drop("*2.py")

        self.assertIn(str(Path("test1.py").resolve()), coder.abs_fnames)
        self.assertNotIn(str(Path("test2.py").resolve()), coder.abs_fnames)

    def test_cmd_add_bad_encoding(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Create a new file foo.bad which will fail to decode as utf-8
        with codecs.open("foo.bad", "w", encoding="iso-8859-15") as f:
            f.write("ÆØÅ")  # Characters not present in utf-8

        commands.cmd_add("foo.bad")

        self.assertEqual(coder.abs_fnames, set())

    def test_cmd_git(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, fancy_input=False, yes=True)

        with GitTemporaryDirectory() as tempdir:
            # Create a file in the temporary directory
            with open(f"{tempdir}/test.txt", "w") as f:
                f.write("test")

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Run the cmd_git method with the arguments "commit -a -m msg"
            commands.cmd_git("add test.txt")
            commands.cmd_git("commit -a -m msg")

            # Check if the file has been committed to the repository
            repo = git.Repo(tempdir)
            files_in_repo = repo.git.ls_files()
            self.assertIn("test.txt", files_in_repo)

    def test_cmd_tokens(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, fancy_input=False, yes=True)

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        commands.cmd_add("foo.txt bar.txt")

        # Redirect the standard output to an instance of io.StringIO
        stdout = StringIO()
        sys.stdout = stdout

        commands.cmd_tokens("")

        # Reset the standard output
        sys.stdout = sys.__stdout__

        # Get the console output
        console_output = stdout.getvalue()

        self.assertIn("foo.txt", console_output)
        self.assertIn("bar.txt", console_output)

    def test_cmd_add_from_subdir(self):
        repo = git.Repo.init()
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "testuser@example.com").release()

        # Create three empty files and add them to the git repository
        filenames = ["one.py", Path("subdir") / "two.py", Path("anotherdir") / "three.py"]
        for filename in filenames:
            file_path = Path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
            repo.git.add(str(file_path))
        repo.git.commit("-m", "added")

        filenames = [str(Path(fn).resolve()) for fn in filenames]

        ###

        os.chdir("subdir")

        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # this should get added
        commands.cmd_add(str(Path("anotherdir") / "three.py"))

        # this should add one.py
        commands.cmd_add("*.py")

        self.assertIn(filenames[0], coder.abs_fnames)
        self.assertNotIn(filenames[1], coder.abs_fnames)
        self.assertIn(filenames[2], coder.abs_fnames)

    def test_cmd_add_from_subdir_again(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            Path("side_dir").mkdir()
            os.chdir("side_dir")

            # add a file that is in the side_dir
            with open("temp.txt", "w"):
                pass

            # this was blowing up with GitCommandError, per:
            # https://github.com/Aider-AI/aider/issues/201
            commands.cmd_add("temp.txt")

    def test_cmd_commit(self):
        with GitTemporaryDirectory():
            fname = "test.txt"
            with open(fname, "w") as f:
                f.write("test")
            repo = git.Repo()
            repo.git.add(fname)
            repo.git.commit("-m", "initial")

            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            self.assertFalse(repo.is_dirty())
            with open(fname, "w") as f:
                f.write("new")
            self.assertTrue(repo.is_dirty())

            commit_message = "Test commit message"
            commands.cmd_commit(commit_message)
            self.assertFalse(repo.is_dirty())

    def test_cmd_add_from_outside_root(self):
        with ChdirTemporaryDirectory() as tmp_dname:
            root = Path("root")
            root.mkdir()
            os.chdir(str(root))

            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            outside_file = Path(tmp_dname) / "outside.txt"
            outside_file.touch()

            # This should not be allowed!
            # https://github.com/Aider-AI/aider/issues/178
            commands.cmd_add("../outside.txt")

            self.assertEqual(len(coder.abs_fnames), 0)

    def test_cmd_add_from_outside_git(self):
        with ChdirTemporaryDirectory() as tmp_dname:
            root = Path("root")
            root.mkdir()
            os.chdir(str(root))

            make_repo()

            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            outside_file = Path(tmp_dname) / "outside.txt"
            outside_file.touch()

            # This should not be allowed!
            # It was blowing up with GitCommandError, per:
            # https://github.com/Aider-AI/aider/issues/178
            commands.cmd_add("../outside.txt")

            self.assertEqual(len(coder.abs_fnames), 0)

    def test_cmd_add_filename_with_special_chars(self):
        with ChdirTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            fname = Path("with[brackets].txt")
            fname.touch()

            commands.cmd_add(str(fname))

            self.assertIn(str(fname.resolve()), coder.abs_fnames)

    def test_cmd_tokens_output(self):
        with GitTemporaryDirectory() as repo_dir:
            # Create a small repository with a few files
            (Path(repo_dir) / "file1.txt").write_text("Content of file 1")
            (Path(repo_dir) / "file2.py").write_text("print('Content of file 2')")
            (Path(repo_dir) / "subdir").mkdir()
            (Path(repo_dir) / "subdir" / "file3.md").write_text("# Content of file 3")

            repo = git.Repo.init(repo_dir)
            repo.git.add(A=True)
            repo.git.commit("-m", "Initial commit")

            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(Model("claude-3-5-sonnet-20240620"), None, io)
            print(coder.get_announcements())
            commands = Commands(io, coder)

            commands.cmd_add("*.txt")

            # Capture the output of cmd_tokens
            original_tool_output = io.tool_output
            output_lines = []

            def capture_output(*args, **kwargs):
                output_lines.extend(args)
                original_tool_output(*args, **kwargs)

            io.tool_output = capture_output

            # Run cmd_tokens
            commands.cmd_tokens("")

            # Restore original tool_output
            io.tool_output = original_tool_output

            # Check if the output includes repository map information
            repo_map_line = next((line for line in output_lines if "repository map" in line), None)
            self.assertIsNotNone(
                repo_map_line, "Repository map information not found in the output"
            )

            # Check if the output includes information about all added files
            self.assertTrue(any("file1.txt" in line for line in output_lines))

            # Check if the total tokens and remaining tokens are reported
            self.assertTrue(any("tokens total" in line for line in output_lines))
            self.assertTrue(any("tokens remaining" in line for line in output_lines))

    def test_cmd_add_dirname_with_special_chars(self):
        with ChdirTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            dname = Path("with[brackets]")
            dname.mkdir()
            fname = dname / "filename.txt"
            fname.touch()

            commands.cmd_add(str(dname))

            dump(coder.abs_fnames)
            self.assertIn(str(fname.resolve()), coder.abs_fnames)

    def test_cmd_add_dirname_with_special_chars_git(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            dname = Path("with[brackets]")
            dname.mkdir()
            fname = dname / "filename.txt"
            fname.touch()

            repo = git.Repo()
            repo.git.add(str(fname))
            repo.git.commit("-m", "init")

            commands.cmd_add(str(dname))

            dump(coder.abs_fnames)
            self.assertIn(str(fname.resolve()), coder.abs_fnames)

    def test_cmd_add_abs_filename(self):
        with ChdirTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            fname = Path("file.txt")
            fname.touch()

            commands.cmd_add(str(fname.resolve()))

            self.assertIn(str(fname.resolve()), coder.abs_fnames)

    def test_cmd_add_quoted_filename(self):
        with ChdirTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            fname = Path("file with spaces.txt")
            fname.touch()

            commands.cmd_add(f'"{fname}"')

            self.assertIn(str(fname.resolve()), coder.abs_fnames)

    def test_cmd_add_existing_with_dirty_repo(self):
        with GitTemporaryDirectory():
            repo = git.Repo()

            files = ["one.txt", "two.txt"]
            for fname in files:
                Path(fname).touch()
                repo.git.add(fname)
            repo.git.commit("-m", "initial")

            commit = repo.head.commit.hexsha

            # leave a dirty `git rm`
            repo.git.rm("one.txt")

            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # There's no reason this /add should trigger a commit
            commands.cmd_add("two.txt")

            self.assertEqual(commit, repo.head.commit.hexsha)

            # Windows is throwing:
            # PermissionError: [WinError 32] The process cannot access
            # the file because it is being used by another process

            repo.git.commit("-m", "cleanup")

            del coder
            del commands
            del repo

    def test_cmd_read_only_with_glob_pattern(self):
        with GitTemporaryDirectory() as repo_dir:
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create multiple test files
            test_files = ["test_file1.txt", "test_file2.txt", "other_file.txt"]
            for file_name in test_files:
                file_path = Path(repo_dir) / file_name
                file_path.write_text(f"Content of {file_name}")

            # Test the /read-only command with a glob pattern
            commands.cmd_read_only("test_*.txt")

            # Check if only the matching files were added to abs_read_only_fnames
            self.assertEqual(len(coder.abs_read_only_fnames), 2)
            for file_name in ["test_file1.txt", "test_file2.txt"]:
                file_path = Path(repo_dir) / file_name
                self.assertTrue(
                    any(
                        os.path.samefile(str(file_path), fname)
                        for fname in coder.abs_read_only_fnames
                    )
                )

            # Check that other_file.txt was not added
            other_file_path = Path(repo_dir) / "other_file.txt"
            self.assertFalse(
                any(
                    os.path.samefile(str(other_file_path), fname)
                    for fname in coder.abs_read_only_fnames
                )
            )

    def test_cmd_read_only_with_recursive_glob(self):
        with GitTemporaryDirectory() as repo_dir:
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create a directory structure with files
            (Path(repo_dir) / "subdir").mkdir()
            test_files = ["test_file1.txt", "subdir/test_file2.txt", "subdir/other_file.txt"]
            for file_name in test_files:
                file_path = Path(repo_dir) / file_name
                file_path.write_text(f"Content of {file_name}")

            # Test the /read-only command with a recursive glob pattern
            commands.cmd_read_only("**/*.txt")

            # Check if all .txt files were added to abs_read_only_fnames
            self.assertEqual(len(coder.abs_read_only_fnames), 3)
            for file_name in test_files:
                file_path = Path(repo_dir) / file_name
                self.assertTrue(
                    any(
                        os.path.samefile(str(file_path), fname)
                        for fname in coder.abs_read_only_fnames
                    )
                )

    def test_cmd_read_only_with_nonexistent_glob(self):
        with GitTemporaryDirectory() as repo_dir:
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Test the /read-only command with a non-existent glob pattern
            with mock.patch.object(io, "tool_error") as mock_tool_error:
                commands.cmd_read_only(str(Path(repo_dir) / "nonexistent*.txt"))

            # Check if the appropriate error message was displayed
            mock_tool_error.assert_called_once_with(
                f"No matches found for: {Path(repo_dir) / 'nonexistent*.txt'}"
            )

            # Ensure no files were added to abs_read_only_fnames
            self.assertEqual(len(coder.abs_read_only_fnames), 0)

    def test_cmd_add_unicode_error(self):
        # Initialize the Commands and InputOutput objects
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        from aider.coders import Coder

        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        fname = "file.txt"
        encoding = "utf-16"
        some_content_which_will_error_if_read_with_encoding_utf8 = "ÅÍÎÏ".encode(encoding)
        with open(fname, "wb") as f:
            f.write(some_content_which_will_error_if_read_with_encoding_utf8)

        commands.cmd_add("file.txt")
        self.assertEqual(coder.abs_fnames, set())

    def test_cmd_add_read_only_file(self):
        with GitTemporaryDirectory():
            # Initialize the Commands and InputOutput objects
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create a test file
            test_file = Path("test_read_only.txt")
            test_file.write_text("Test content")

            # Add the file as read-only
            commands.cmd_read_only(str(test_file))

            # Verify it's in abs_read_only_fnames
            self.assertTrue(
                any(
                    os.path.samefile(str(test_file.resolve()), fname)
                    for fname in coder.abs_read_only_fnames
                )
            )

            # Try to add the read-only file
            commands.cmd_add(str(test_file))

            # It's not in the repo, should not do anything
            self.assertFalse(
                any(os.path.samefile(str(test_file.resolve()), fname) for fname in coder.abs_fnames)
            )
            self.assertTrue(
                any(
                    os.path.samefile(str(test_file.resolve()), fname)
                    for fname in coder.abs_read_only_fnames
                )
            )

            repo = git.Repo()
            repo.git.add(str(test_file))
            repo.git.commit("-m", "initial")

            # Try to add the read-only file
            commands.cmd_add(str(test_file))

            # Verify it's now in abs_fnames and not in abs_read_only_fnames
            self.assertTrue(
                any(os.path.samefile(str(test_file.resolve()), fname) for fname in coder.abs_fnames)
            )
            self.assertFalse(
                any(
                    os.path.samefile(str(test_file.resolve()), fname)
                    for fname in coder.abs_read_only_fnames
                )
            )

    def test_cmd_test_unbound_local_error(self):
        with ChdirTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Mock the io.prompt_ask method to simulate user input
            io.prompt_ask = lambda *args, **kwargs: "y"

            # Test the cmd_run method with a command that should not raise an error
            result = commands.cmd_run("exit 1", add_on_nonzero_exit=True)
            self.assertIn("I ran this command", result)

    def test_cmd_add_drop_untracked_files(self):
        with GitTemporaryDirectory():
            repo = git.Repo()

            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            from aider.coders import Coder

            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            fname = Path("test.txt")
            fname.touch()

            self.assertEqual(len(coder.abs_fnames), 0)

            commands.cmd_add(str(fname))

            files_in_repo = repo.git.ls_files()
            self.assertNotIn(str(fname), files_in_repo)

            self.assertEqual(len(coder.abs_fnames), 1)

            commands.cmd_drop(str(fname))

            self.assertEqual(len(coder.abs_fnames), 0)

    def test_cmd_undo_with_dirty_files_not_in_last_commit(self):
        with GitTemporaryDirectory() as repo_dir:
            repo = git.Repo(repo_dir)
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            other_path = Path(repo_dir) / "other_file.txt"
            other_path.write_text("other content")
            repo.git.add(str(other_path))

            # Create and commit a file
            filename = "test_file.txt"
            file_path = Path(repo_dir) / filename
            file_path.write_text("first content")
            repo.git.add(filename)
            repo.git.commit("-m", "first commit")

            file_path.write_text("second content")
            repo.git.add(filename)
            repo.git.commit("-m", "second commit")

            # Store the commit hash
            last_commit_hash = repo.head.commit.hexsha[:7]
            coder.aider_commit_hashes.add(last_commit_hash)

            file_path.write_text("dirty content")

            # Attempt to undo the last commit
            commands.cmd_undo("")

            # Check that the last commit is still present
            self.assertEqual(last_commit_hash, repo.head.commit.hexsha[:7])

            # Put back the initial content (so it's not dirty now)
            file_path.write_text("second content")
            other_path.write_text("dirty content")

            commands.cmd_undo("")
            self.assertNotEqual(last_commit_hash, repo.head.commit.hexsha[:7])

            self.assertEqual(file_path.read_text(), "first content")
            self.assertEqual(other_path.read_text(), "dirty content")

            del coder
            del commands
            del repo

    def test_cmd_undo_with_newly_committed_file(self):
        with GitTemporaryDirectory() as repo_dir:
            repo = git.Repo(repo_dir)
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Put in a random first commit
            filename = "first_file.txt"
            file_path = Path(repo_dir) / filename
            file_path.write_text("new file content")
            repo.git.add(filename)
            repo.git.commit("-m", "Add new file")

            # Create and commit a new file
            filename = "new_file.txt"
            file_path = Path(repo_dir) / filename
            file_path.write_text("new file content")
            repo.git.add(filename)
            repo.git.commit("-m", "Add new file")

            # Store the commit hash
            last_commit_hash = repo.head.commit.hexsha[:7]
            coder.aider_commit_hashes.add(last_commit_hash)

            # Attempt to undo the last commit, should refuse
            commands.cmd_undo("")

            # Check that the last commit was not undone
            self.assertEqual(last_commit_hash, repo.head.commit.hexsha[:7])
            self.assertTrue(file_path.exists())

            del coder
            del commands
            del repo

    def test_cmd_undo_on_first_commit(self):
        with GitTemporaryDirectory() as repo_dir:
            repo = git.Repo(repo_dir)
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create and commit a new file
            filename = "new_file.txt"
            file_path = Path(repo_dir) / filename
            file_path.write_text("new file content")
            repo.git.add(filename)
            repo.git.commit("-m", "Add new file")

            # Store the commit hash
            last_commit_hash = repo.head.commit.hexsha[:7]
            coder.aider_commit_hashes.add(last_commit_hash)

            # Attempt to undo the last commit
            commands.cmd_undo("")

            # Check that the commit is still present
            self.assertEqual(last_commit_hash, repo.head.commit.hexsha[:7])
            self.assertTrue(file_path.exists())

            del coder
            del commands
            del repo

    def test_cmd_add_aiderignored_file(self):
        with GitTemporaryDirectory():
            repo = git.Repo()

            fname1 = "ignoreme1.txt"
            fname2 = "ignoreme2.txt"
            fname3 = "dir/ignoreme3.txt"

            Path(fname2).touch()
            repo.git.add(str(fname2))
            repo.git.commit("-m", "initial")

            aignore = Path(".aiderignore")
            aignore.write_text(f"{fname1}\n{fname2}\ndir\n")

            io = InputOutput(yes=True)

            fnames = [fname1, fname2]
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
            commands = Commands(io, coder)

            commands.cmd_add(f"{fname1} {fname2} {fname3}")

            self.assertNotIn(fname1, str(coder.abs_fnames))
            self.assertNotIn(fname2, str(coder.abs_fnames))
            self.assertNotIn(fname3, str(coder.abs_fnames))

    def test_cmd_read_only(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create a test file
            test_file = Path("test_read.txt")
            test_file.write_text("Test content")

            # Test the /read command
            commands.cmd_read_only(str(test_file))

            # Check if the file was added to abs_read_only_fnames
            self.assertTrue(
                any(
                    os.path.samefile(str(test_file.resolve()), fname)
                    for fname in coder.abs_read_only_fnames
                )
            )

            # Test dropping the read-only file
            commands.cmd_drop(str(test_file))

            # Check if the file was removed from abs_read_only_fnames
            self.assertFalse(
                any(
                    os.path.samefile(str(test_file.resolve()), fname)
                    for fname in coder.abs_read_only_fnames
                )
            )

    def test_cmd_read_only_from_working_dir(self):
        with GitTemporaryDirectory() as repo_dir:
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create a subdirectory and a test file within it
            subdir = Path(repo_dir) / "subdir"
            subdir.mkdir()
            test_file = subdir / "test_read_only_file.txt"
            test_file.write_text("Test content")

            # Change the current working directory to the subdirectory
            os.chdir(subdir)

            # Test the /read-only command using git_root referenced name
            commands.cmd_read_only(os.path.join("subdir", "test_read_only_file.txt"))

            # Check if the file was added to abs_read_only_fnames
            self.assertTrue(
                any(
                    os.path.samefile(str(test_file.resolve()), fname)
                    for fname in coder.abs_read_only_fnames
                )
            )

            # Test dropping the read-only file using git_root referenced name
            commands.cmd_drop(os.path.join("subdir", "test_read_only_file.txt"))

            # Check if the file was removed from abs_read_only_fnames
            self.assertFalse(
                any(
                    os.path.samefile(str(test_file.resolve()), fname)
                    for fname in coder.abs_read_only_fnames
                )
            )

    def test_cmd_read_only_with_external_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as external_file:
            external_file.write("External file content")
            external_file_path = external_file.name

        try:
            with GitTemporaryDirectory():
                io = InputOutput(pretty=False, fancy_input=False, yes=False)
                coder = Coder.create(self.GPT35, None, io)
                commands = Commands(io, coder)

                # Test the /read command with an external file
                commands.cmd_read_only(external_file_path)

                # Check if the external file was added to abs_read_only_fnames
                real_external_file_path = os.path.realpath(external_file_path)
                self.assertTrue(
                    any(
                        os.path.samefile(real_external_file_path, fname)
                        for fname in coder.abs_read_only_fnames
                    )
                )

                # Test dropping the external read-only file
                commands.cmd_drop(Path(external_file_path).name)

                # Check if the file was removed from abs_read_only_fnames
                self.assertFalse(
                    any(
                        os.path.samefile(real_external_file_path, fname)
                        for fname in coder.abs_read_only_fnames
                    )
                )
        finally:
            os.unlink(external_file_path)

    def test_cmd_read_only_with_multiple_files(self):
        with GitTemporaryDirectory() as repo_dir:
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create multiple test files
            test_files = ["test_file1.txt", "test_file2.txt", "test_file3.txt"]
            for file_name in test_files:
                file_path = Path(repo_dir) / file_name
                file_path.write_text(f"Content of {file_name}")

            # Test the /read-only command with multiple files
            commands.cmd_read_only(" ".join(test_files))

            # Check if all test files were added to abs_read_only_fnames
            for file_name in test_files:
                file_path = Path(repo_dir) / file_name
                self.assertTrue(
                    any(
                        os.path.samefile(str(file_path), fname)
                        for fname in coder.abs_read_only_fnames
                    )
                )

            # Test dropping all read-only files
            commands.cmd_drop(" ".join(test_files))

            # Check if all files were removed from abs_read_only_fnames
            self.assertEqual(len(coder.abs_read_only_fnames), 0)

    def test_cmd_read_only_with_tilde_path(self):
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=False)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create a test file in the user's home directory
            home_dir = os.path.expanduser("~")
            test_file = Path(home_dir) / "test_read_only_file.txt"
            test_file.write_text("Test content")

            try:
                # Test the /read-only command with a path in the user's home directory
                relative_path = os.path.join("~", "test_read_only_file.txt")
                commands.cmd_read_only(relative_path)

                # Check if the file was added to abs_read_only_fnames
                self.assertTrue(
                    any(
                        os.path.samefile(str(test_file), fname)
                        for fname in coder.abs_read_only_fnames
                    )
                )

                # Test dropping the read-only file
                commands.cmd_drop(relative_path)

                # Check if the file was removed from abs_read_only_fnames
                self.assertEqual(len(coder.abs_read_only_fnames), 0)

            finally:
                # Clean up: remove the test file from the home directory
                test_file.unlink()

    def test_cmd_diff(self):
        with GitTemporaryDirectory() as repo_dir:
            repo = git.Repo(repo_dir)
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create and commit a file
            filename = "test_file.txt"
            file_path = Path(repo_dir) / filename
            file_path.write_text("Initial content\n")
            repo.git.add(filename)
            repo.git.commit("-m", "Initial commit\n")

            # Modify the file to make it dirty
            file_path.write_text("Modified content")

            # Mock repo.get_commit_message to return a canned commit message
            with mock.patch.object(
                coder.repo, "get_commit_message", return_value="Canned commit message"
            ):
                # Run cmd_commit
                commands.cmd_commit()

                # Capture the output of cmd_diff
                with mock.patch("builtins.print") as mock_print:
                    commands.cmd_diff("")

                # Check if the diff output is correct
                mock_print.assert_called_with(mock.ANY)
                diff_output = mock_print.call_args[0][0]
                self.assertIn("-Initial content", diff_output)
                self.assertIn("+Modified content", diff_output)

                # Modify the file again
                file_path.write_text("Further modified content")

                # Run cmd_commit again
                commands.cmd_commit()

                # Capture the output of cmd_diff
                with mock.patch("builtins.print") as mock_print:
                    commands.cmd_diff("")

                # Check if the diff output is correct
                mock_print.assert_called_with(mock.ANY)
                diff_output = mock_print.call_args[0][0]
                self.assertIn("-Modified content", diff_output)
                self.assertIn("+Further modified content", diff_output)

                # Modify the file a third time
                file_path.write_text("Final modified content")

                # Run cmd_commit again
                commands.cmd_commit()

                # Capture the output of cmd_diff
                with mock.patch("builtins.print") as mock_print:
                    commands.cmd_diff("")

                # Check if the diff output is correct
                mock_print.assert_called_with(mock.ANY)
                diff_output = mock_print.call_args[0][0]
                self.assertIn("-Further modified content", diff_output)
                self.assertIn("+Final modified content", diff_output)

    def test_cmd_ask(self):
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        question = "What is the meaning of life?"
        canned_reply = "The meaning of life is 42."

        with mock.patch("aider.coders.Coder.run") as mock_run:
            mock_run.return_value = canned_reply

            with self.assertRaises(SwitchCoder):
                commands.cmd_ask(question)

            mock_run.assert_called_once()
            mock_run.assert_called_once_with(question)

    def test_cmd_lint_with_dirty_file(self):
        with GitTemporaryDirectory() as repo_dir:
            repo = git.Repo(repo_dir)
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Create and commit a file
            filename = "test_file.py"
            file_path = Path(repo_dir) / filename
            file_path.write_text("def hello():\n    print('Hello, World!')\n")
            repo.git.add(filename)
            repo.git.commit("-m", "Add test_file.py")

            # Modify the file to make it dirty
            file_path.write_text("def hello():\n    print('Hello, World!')\n\n# Dirty line\n")

            # Mock the linter.lint method
            with mock.patch.object(coder.linter, "lint") as mock_lint:
                # Set up the mock to return an empty string (no lint errors)
                mock_lint.return_value = ""

                # Run cmd_lint
                commands.cmd_lint()

                # Check if the linter was called with a filename string
                # whose Path().name matches the expected filename
                mock_lint.assert_called_once()
                called_arg = mock_lint.call_args[0][0]
                self.assertEqual(Path(called_arg).name, filename)

            # Verify that the file is still dirty after linting
            self.assertTrue(repo.is_dirty(filename))

            del coder
            del commands
            del repo

    def test_cmd_reset(self):
        with GitTemporaryDirectory() as repo_dir:
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = Coder.create(self.GPT35, None, io)
            commands = Commands(io, coder)

            # Add some files to the chat
            file1 = Path(repo_dir) / "file1.txt"
            file2 = Path(repo_dir) / "file2.txt"
            file1.write_text("Content of file 1")
            file2.write_text("Content of file 2")
            commands.cmd_add(f"{file1} {file2}")

            # Add some messages to the chat history
            coder.cur_messages = [{"role": "user", "content": "Test message 1"}]
            coder.done_messages = [{"role": "assistant", "content": "Test message 2"}]

            # Run the reset command
            commands.cmd_reset("")

            # Check that all files have been dropped
            self.assertEqual(len(coder.abs_fnames), 0)
            self.assertEqual(len(coder.abs_read_only_fnames), 0)

            # Check that the chat history has been cleared
            self.assertEqual(len(coder.cur_messages), 0)
            self.assertEqual(len(coder.done_messages), 0)

            # Verify that the files still exist in the repository
            self.assertTrue(file1.exists())
            self.assertTrue(file2.exists())

            del coder
            del commands
