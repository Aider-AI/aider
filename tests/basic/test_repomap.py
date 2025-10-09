import difflib
import os
import re
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import git

from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.models import Model
from aider.repomap import RepoMap
from aider.utils import GitTemporaryDirectory, IgnorantTemporaryDirectory


class TestRepoMap(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")

    # Helper function to calculate MD5 hash of a file
    def _calculate_md5_for_file(self, file_path):
        import hashlib
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def test_get_repo_map(self):
        pass

    @patch("aider.io.InputOutput.tool_warning")
    def test_get_tags_md5_change_same_mtime(self, mock_tool_warning):
        """Verify MD5 detection when mtime is unchanged."""
        with GitTemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = Path(temp_dir) / "test.py"
            initial_content = "def func_a(): pass\n"
            test_file.write_text(initial_content)
            abs_path = str(test_file.resolve())
            rel_path = "test.py"

            # Initialize RepoMap and populate cache
            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            initial_tags = repo_map.get_tags(abs_path, rel_path)
            self.assertTrue(any(tag.name == "func_a" for tag in initial_tags))
            initial_mtime = os.path.getmtime(abs_path)

            # Modify content, reset mtime
            new_content = "def func_b(): pass\n"
            test_file.write_text(new_content)
            os.utime(abs_path, (initial_mtime, initial_mtime)) # Reset mtime

            # Call get_tags again
            new_tags = repo_map.get_tags(abs_path, rel_path)

            # Assertions
            mock_tool_warning.assert_called_once()
            self.assertIn("MD5 mismatch", mock_tool_warning.call_args[0][0])
            self.assertTrue(any(tag.name == "func_b" for tag in new_tags))
            self.assertFalse(any(tag.name == "func_a" for tag in new_tags))

            # Check cache update
            cached_data = repo_map.TAGS_CACHE.get(abs_path)
            self.assertIsNotNone(cached_data)
            expected_md5 = self._calculate_md5_for_file(abs_path)
            self.assertEqual(cached_data.get("md5"), expected_md5)
            self.assertEqual(cached_data.get("mtime"), initial_mtime)

            del repo_map # Close cache

    @patch("aider.io.InputOutput.tool_warning")
    @patch("aider.repomap.RepoMap.get_tags_raw")
    def test_get_tags_no_change(self, mock_get_tags_raw, mock_tool_warning):
        """Verify cache is used when file is unchanged."""
        with GitTemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            initial_content = "def func_a(): pass\n"
            test_file.write_text(initial_content)
            abs_path = str(test_file.resolve())
            rel_path = "test.py"

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)

            # Initial call to populate cache
            initial_tags = repo_map.get_tags(abs_path, rel_path)
            mock_get_tags_raw.assert_called_once() # Called once initially
            mock_get_tags_raw.reset_mock() # Reset for the next check

            # Call get_tags again without changes
            second_tags = repo_map.get_tags(abs_path, rel_path)

            # Assertions
            mock_tool_warning.assert_not_called()
            mock_get_tags_raw.assert_not_called() # Should not be called again
            self.assertEqual(initial_tags, second_tags)

            del repo_map # Close cache

    @patch("aider.io.InputOutput.tool_warning")
    def test_get_tags_mtime_change(self, mock_tool_warning):
        """Verify standard mtime-based change detection still works."""
        with GitTemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            initial_content = "def func_a(): pass\n"
            test_file.write_text(initial_content)
            abs_path = str(test_file.resolve())
            rel_path = "test.py"

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)

            # Initial call
            initial_tags = repo_map.get_tags(abs_path, rel_path)
            self.assertTrue(any(tag.name == "func_a" for tag in initial_tags))

            # Modify content (mtime will change naturally)
            time.sleep(0.01) # Ensure mtime is different
            new_content = "def func_b(): pass\n"
            test_file.write_text(new_content)
            new_mtime = os.path.getmtime(abs_path)

            # Call get_tags again
            new_tags = repo_map.get_tags(abs_path, rel_path)

            # Assertions
            mock_tool_warning.assert_called_once()
            self.assertIn("mtime mismatch", mock_tool_warning.call_args[0][0])
            self.assertTrue(any(tag.name == "func_b" for tag in new_tags))
            self.assertFalse(any(tag.name == "func_a" for tag in new_tags))

            # Check cache update
            cached_data = repo_map.TAGS_CACHE.get(abs_path)
            self.assertIsNotNone(cached_data)
            expected_md5 = self._calculate_md5_for_file(abs_path)
            self.assertEqual(cached_data.get("md5"), expected_md5)
            self.assertEqual(cached_data.get("mtime"), new_mtime)

            del repo_map # Close cache

    @patch("aider.io.InputOutput.tool_warning")
    def test_get_tags_file_not_found_after_cache(self, mock_tool_warning):
        """Verify graceful handling if a cached file becomes inaccessible."""
        with GitTemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.py"
            test_file.write_text("def func_a(): pass\n")
            abs_path = str(test_file.resolve())
            rel_path = "test.py"

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)

            # Populate cache
            repo_map.get_tags(abs_path, rel_path)
            self.assertIn(abs_path, repo_map.TAGS_CACHE)

            # Delete the file
            os.remove(abs_path)

            # Call get_tags again
            result = repo_map.get_tags(abs_path, rel_path)

            # Assertions
            mock_tool_warning.assert_called()
            # Check if any call contains "Error accessing file" or "FileNotFoundError"
            warning_found = any(
                "Error accessing file" in call[0][0] or "FileNotFoundError" in call[0][0]
                for call in mock_tool_warning.call_args_list
            )
            self.assertTrue(warning_found, "Expected file access error warning not found")

            self.assertEqual(result, [])
            self.assertNotIn(abs_path, repo_map.TAGS_CACHE)

            del repo_map # Close cache
        # Create a temporary directory with sample files for testing
        test_files = [
            "test_file1.py",
            "test_file2.py",
            "test_file3.md",
            "test_file4.json",
        ]

        with IgnorantTemporaryDirectory() as temp_dir:
            for file in test_files:
                with open(os.path.join(temp_dir, file), "w") as f:
                    f.write("")

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            other_files = [os.path.join(temp_dir, file) for file in test_files]
            result = repo_map.get_repo_map([], other_files)

            # Check if the result contains the expected tags map
            self.assertIn("test_file1.py", result)
            self.assertIn("test_file2.py", result)
            self.assertIn("test_file3.md", result)
            self.assertIn("test_file4.json", result)

            # close the open cache files, so Windows won't error
            del repo_map

    def test_repo_map_refresh_files(self):
        with GitTemporaryDirectory() as temp_dir:
            repo = git.Repo(temp_dir)

            # Create three source files with one function each
            file1_content = "def function1():\n    return 'Hello from file1'\n"
            file2_content = "def function2():\n    return 'Hello from file2'\n"
            file3_content = "def function3():\n    return 'Hello from file3'\n"

            with open(os.path.join(temp_dir, "file1.py"), "w") as f:
                f.write(file1_content)
            with open(os.path.join(temp_dir, "file2.py"), "w") as f:
                f.write(file2_content)
            with open(os.path.join(temp_dir, "file3.py"), "w") as f:
                f.write(file3_content)

            # Add files to git
            repo.index.add(["file1.py", "file2.py", "file3.py"])
            repo.index.commit("Initial commit")

            # Initialize RepoMap with refresh="files"
            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io, refresh="files")
            other_files = [
                os.path.join(temp_dir, "file1.py"),
                os.path.join(temp_dir, "file2.py"),
                os.path.join(temp_dir, "file3.py"),
            ]

            # Get initial repo map
            initial_map = repo_map.get_repo_map([], other_files)
            dump(initial_map)
            self.assertIn("function1", initial_map)
            self.assertIn("function2", initial_map)
            self.assertIn("function3", initial_map)

            # Add a new function to file1.py
            with open(os.path.join(temp_dir, "file1.py"), "a") as f:
                f.write("\ndef functionNEW():\n    return 'Hello NEW'\n")

            # Get another repo map
            second_map = repo_map.get_repo_map([], other_files)
            self.assertEqual(
                initial_map, second_map, "RepoMap should not change with refresh='files'"
            )

            other_files = [
                os.path.join(temp_dir, "file1.py"),
                os.path.join(temp_dir, "file2.py"),
            ]
            second_map = repo_map.get_repo_map([], other_files)
            self.assertIn("functionNEW", second_map)

            # close the open cache files, so Windows won't error
            del repo_map
            del repo

    def test_repo_map_refresh_auto(self):
        with GitTemporaryDirectory() as temp_dir:
            repo = git.Repo(temp_dir)

            # Create two source files with one function each
            file1_content = "def function1():\n    return 'Hello from file1'\n"
            file2_content = "def function2():\n    return 'Hello from file2'\n"

            with open(os.path.join(temp_dir, "file1.py"), "w") as f:
                f.write(file1_content)
            with open(os.path.join(temp_dir, "file2.py"), "w") as f:
                f.write(file2_content)

            # Add files to git
            repo.index.add(["file1.py", "file2.py"])
            repo.index.commit("Initial commit")

            # Initialize RepoMap with refresh="auto"
            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io, refresh="auto")
            chat_files = []
            other_files = [os.path.join(temp_dir, "file1.py"), os.path.join(temp_dir, "file2.py")]

            # Force the RepoMap computation to take more than 1 second
            original_get_ranked_tags = repo_map.get_ranked_tags

            def slow_get_ranked_tags(*args, **kwargs):
                time.sleep(1.1)  # Sleep for 1.1 seconds to ensure it's over 1 second
                return original_get_ranked_tags(*args, **kwargs)

            repo_map.get_ranked_tags = slow_get_ranked_tags

            # Get initial repo map
            initial_map = repo_map.get_repo_map(chat_files, other_files)
            self.assertIn("function1", initial_map)
            self.assertIn("function2", initial_map)
            self.assertNotIn("functionNEW", initial_map)

            # Add a new function to file1.py
            with open(os.path.join(temp_dir, "file1.py"), "a") as f:
                f.write("\ndef functionNEW():\n    return 'Hello NEW'\n")

            # Get another repo map without force_refresh
            second_map = repo_map.get_repo_map(chat_files, other_files)
            self.assertEqual(
                initial_map, second_map, "RepoMap should not change without force_refresh"
            )

            # Get a new repo map with force_refresh
            final_map = repo_map.get_repo_map(chat_files, other_files, force_refresh=True)
            self.assertIn("functionNEW", final_map)
            self.assertNotEqual(initial_map, final_map, "RepoMap should change with force_refresh")

            # close the open cache files, so Windows won't error
            del repo_map
            del repo

    def test_get_repo_map_with_identifiers(self):
        # Create a temporary directory with a sample Python file containing identifiers
        test_file1 = "test_file_with_identifiers.py"
        file_content1 = """\
class MyClass:
    def my_method(self, arg1, arg2):
        return arg1 + arg2

def my_function(arg1, arg2):
    return arg1 * arg2
"""

        test_file2 = "test_file_import.py"
        file_content2 = """\
from test_file_with_identifiers import MyClass

obj = MyClass()
print(obj.my_method(1, 2))
print(my_function(3, 4))
"""

        test_file3 = "test_file_pass.py"
        file_content3 = "pass"

        with IgnorantTemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, test_file1), "w") as f:
                f.write(file_content1)

            with open(os.path.join(temp_dir, test_file2), "w") as f:
                f.write(file_content2)

            with open(os.path.join(temp_dir, test_file3), "w") as f:
                f.write(file_content3)

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            other_files = [
                os.path.join(temp_dir, test_file1),
                os.path.join(temp_dir, test_file2),
                os.path.join(temp_dir, test_file3),
            ]
            result = repo_map.get_repo_map([], other_files)

            # Check if the result contains the expected tags map with identifiers
            self.assertIn("test_file_with_identifiers.py", result)
            self.assertIn("MyClass", result)
            self.assertIn("my_method", result)
            self.assertIn("my_function", result)
            self.assertIn("test_file_pass.py", result)

            # close the open cache files, so Windows won't error
            del repo_map

    def test_get_repo_map_all_files(self):
        test_files = [
            "test_file0.py",
            "test_file1.txt",
            "test_file2.md",
            "test_file3.json",
            "test_file4.html",
            "test_file5.css",
            "test_file6.js",
        ]

        with IgnorantTemporaryDirectory() as temp_dir:
            for file in test_files:
                with open(os.path.join(temp_dir, file), "w") as f:
                    f.write("")

            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=InputOutput())

            other_files = [os.path.join(temp_dir, file) for file in test_files]
            result = repo_map.get_repo_map([], other_files)
            dump(other_files)
            dump(repr(result))

            # Check if the result contains each specific file in the expected tags map without ctags
            for file in test_files:
                self.assertIn(file, result)

            # close the open cache files, so Windows won't error
            del repo_map

    def test_get_repo_map_excludes_added_files(self):
        # Create a temporary directory with sample files for testing
        test_files = [
            "test_file1.py",
            "test_file2.py",
            "test_file3.md",
            "test_file4.json",
        ]

        with IgnorantTemporaryDirectory() as temp_dir:
            for file in test_files:
                with open(os.path.join(temp_dir, file), "w") as f:
                    f.write("def foo(): pass\n")

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            test_files = [os.path.join(temp_dir, file) for file in test_files]
            result = repo_map.get_repo_map(test_files[:2], test_files[2:])

            dump(result)

            # Check if the result contains the expected tags map
            self.assertNotIn("test_file1.py", result)
            self.assertNotIn("test_file2.py", result)
            self.assertIn("test_file3.md", result)
            self.assertIn("test_file4.json", result)

            # close the open cache files, so Windows won't error
            del repo_map


class TestRepoMapTypescript(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")


class TestRepoMapAllLanguages(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")
        self.fixtures_dir = Path(__file__).parent.parent / "fixtures" / "languages"

    def test_language_c(self):
        self._test_language_repo_map("c", "c", "main")

    def test_language_cpp(self):
        self._test_language_repo_map("cpp", "cpp", "main")

    def test_language_d(self):
        self._test_language_repo_map("d", "d", "main")

    def test_language_dart(self):
        self._test_language_repo_map("dart", "dart", "Person")

    def test_language_elixir(self):
        self._test_language_repo_map("elixir", "ex", "Greeter")

    def test_language_gleam(self):
        self._test_language_repo_map("gleam", "gleam", "greet")

    def test_language_java(self):
        self._test_language_repo_map("java", "java", "Greeting")

    def test_language_javascript(self):
        self._test_language_repo_map("javascript", "js", "Person")

    def test_language_kotlin(self):
        self._test_language_repo_map("kotlin", "kt", "Greeting")

    def test_language_lua(self):
        self._test_language_repo_map("lua", "lua", "greet")

    def test_language_php(self):
        self._test_language_repo_map("php", "php", "greet")

    def test_language_python(self):
        self._test_language_repo_map("python", "py", "Person")

    # "ql": ("ql", "greet"), # not supported in tsl-pack (yet?)

    def test_language_ruby(self):
        self._test_language_repo_map("ruby", "rb", "greet")

    def test_language_rust(self):
        self._test_language_repo_map("rust", "rs", "Person")

    def test_language_typescript(self):
        self._test_language_repo_map("typescript", "ts", "greet")

    def test_language_tsx(self):
        self._test_language_repo_map("tsx", "tsx", "UserProps")

    def test_language_csharp(self):
        self._test_language_repo_map("csharp", "cs", "IGreeter")

    def test_language_elisp(self):
        self._test_language_repo_map("elisp", "el", "greeter")

    def test_language_elm(self):
        self._test_language_repo_map("elm", "elm", "Person")

    def test_language_go(self):
        self._test_language_repo_map("go", "go", "Greeter")

    def test_language_hcl(self):
        self._test_language_repo_map("hcl", "tf", "aws_vpc")

    def test_language_arduino(self):
        self._test_language_repo_map("arduino", "ino", "setup")

    def test_language_chatito(self):
        self._test_language_repo_map("chatito", "chatito", "intent")

    def test_language_clojure(self):
        self._test_language_repo_map("clojure", "clj", "greet")

    def test_language_commonlisp(self):
        self._test_language_repo_map("commonlisp", "lisp", "greet")

    def test_language_pony(self):
        self._test_language_repo_map("pony", "pony", "Greeter")

    def test_language_properties(self):
        self._test_language_repo_map("properties", "properties", "database.url")

    def test_language_r(self):
        self._test_language_repo_map("r", "r", "calculate")

    def test_language_racket(self):
        self._test_language_repo_map("racket", "rkt", "greet")

    def test_language_solidity(self):
        self._test_language_repo_map("solidity", "sol", "SimpleStorage")

    def test_language_swift(self):
        self._test_language_repo_map("swift", "swift", "Greeter")

    def test_language_udev(self):
        self._test_language_repo_map("udev", "rules", "USB_DRIVER")

    def test_language_scala(self):
        self._test_language_repo_map("scala", "scala", "Greeter")

    def test_language_ocaml(self):
        self._test_language_repo_map("ocaml", "ml", "Greeter")

    def test_language_ocaml_interface(self):
        self._test_language_repo_map("ocaml_interface", "mli", "Greeter")

    def test_language_matlab(self):
        self._test_language_repo_map("matlab", "m", "Person")

    def _test_language_repo_map(self, lang, key, symbol):
        """Helper method to test repo map generation for a specific language."""
        # Get the fixture file path and name based on language
        fixture_dir = self.fixtures_dir / lang
        filename = f"test.{key}"
        fixture_path = fixture_dir / filename
        self.assertTrue(fixture_path.exists(), f"Fixture file missing for {lang}: {fixture_path}")

        # Read the fixture content
        with open(fixture_path, "r", encoding="utf-8") as f:
            content = f.read()
        with GitTemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, filename)
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            other_files = [test_file]
            result = repo_map.get_repo_map([], other_files)
            dump(lang)
            dump(result)

            print(result)
            self.assertGreater(len(result.strip().splitlines()), 1)

            # Check if the result contains all the expected files and symbols
            self.assertIn(
                filename, result, f"File for language {lang} not found in repo map: {result}"
            )
            self.assertIn(
                symbol,
                result,
                f"Key symbol '{symbol}' for language {lang} not found in repo map: {result}",
            )

            # close the open cache files, so Windows won't error
            del repo_map

    def test_repo_map_sample_code_base(self):
        # Path to the sample code base
        sample_code_base = Path(__file__).parent.parent / "fixtures" / "sample-code-base"

        # Path to the expected repo map file
        expected_map_file = (
            Path(__file__).parent.parent / "fixtures" / "sample-code-base-repo-map.txt"
        )

        # Ensure the paths exist
        self.assertTrue(sample_code_base.exists(), "Sample code base directory not found")
        self.assertTrue(expected_map_file.exists(), "Expected repo map file not found")

        # Initialize RepoMap with the sample code base as root
        io = InputOutput()
        repomap_root = Path(__file__).parent.parent.parent
        repo_map = RepoMap(
            main_model=self.GPT35,
            root=str(repomap_root),
            io=io,
        )

        # Get all files in the sample code base
        other_files = [str(f) for f in sample_code_base.rglob("*") if f.is_file()]

        # Generate the repo map
        generated_map_str = repo_map.get_repo_map([], other_files).strip()

        # Read the expected map from the file using UTF-8 encoding
        with open(expected_map_file, "r", encoding="utf-8") as f:
            expected_map = f.read().strip()

        # Normalize path separators for Windows
        if os.name == "nt":  # Check if running on Windows
            expected_map = re.sub(
                r"tests/fixtures/sample-code-base/([^:]+)",
                r"tests\\fixtures\\sample-code-base\\\1",
                expected_map,
            )
            generated_map_str = re.sub(
                r"tests/fixtures/sample-code-base/([^:]+)",
                r"tests\\fixtures\\sample-code-base\\\1",
                generated_map_str,
            )

        # Compare the generated map with the expected map
        if generated_map_str != expected_map:
            # If they differ, show the differences and fail the test
            diff = list(
                difflib.unified_diff(
                    expected_map.splitlines(),
                    generated_map_str.splitlines(),
                    fromfile="expected",
                    tofile="generated",
                    lineterm="",
                )
            )
            diff_str = "\n".join(diff)
            self.fail(f"Generated map differs from expected map:\n{diff_str}")

        # If we reach here, the maps are identical
        self.assertEqual(generated_map_str, expected_map, "Generated map matches expected map")


if __name__ == "__main__":
    unittest.main()
