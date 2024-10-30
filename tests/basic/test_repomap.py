import difflib
import os
import re
import time
import unittest
from pathlib import Path

import git

from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.models import Model
from aider.repomap import RepoMap
from aider.utils import GitTemporaryDirectory, IgnorantTemporaryDirectory


class TestRepoMap(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")

    def test_get_repo_map(self):
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

    def test_get_repo_map_typescript(self):
        # Create a temporary directory with a sample TypeScript file
        test_file_ts = "test_file.ts"
        file_content_ts = """\
interface IMyInterface {
    someMethod(): void;
}

type ExampleType = {
    key: string;
    value: number;
};

enum Status {
    New,
    InProgress,
    Completed,
}

export class MyClass {
    constructor(public value: number) {}

    add(input: number): number {
        return this.value + input;
        return this.value + input;
    }
}

export function myFunction(input: number): number {
    return input * 2;
}
"""

        with IgnorantTemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, test_file_ts), "w") as f:
                f.write(file_content_ts)

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            other_files = [os.path.join(temp_dir, test_file_ts)]
            result = repo_map.get_repo_map([], other_files)

            # Check if the result contains the expected tags map with TypeScript identifiers
            self.assertIn("test_file.ts", result)
            self.assertIn("IMyInterface", result)
            self.assertIn("ExampleType", result)
            self.assertIn("Status", result)
            self.assertIn("MyClass", result)
            self.assertIn("add", result)
            self.assertIn("myFunction", result)

            # close the open cache files, so Windows won't error
            del repo_map

    def test_get_repo_map_tsx(self):
        # Create a temporary directory with a sample TSX file
        test_file_tsx = "test_file.tsx"
        file_content_tsx = """\
import React from 'react';

interface GreetingProps {
    name: string;
}

const Greeting: React.FC<GreetingProps> = ({ name }) => {
    return <h1>Hello, {name}!</h1>;
};

export default Greeting;
"""

        with IgnorantTemporaryDirectory() as temp_dir:
            with open(os.path.join(temp_dir, test_file_tsx), "w") as f:
                f.write(file_content_tsx)

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            other_files = [os.path.join(temp_dir, test_file_tsx)]
            result = repo_map.get_repo_map([], other_files)

            # Check if the result contains the expected tags map with TSX identifiers
            self.assertIn("test_file.tsx", result)
            self.assertIn("GreetingProps", result)
            self.assertIn("Greeting", result)

            # close the open cache files, so Windows won't error
            del repo_map


class TestRepoMapAllLanguages(unittest.TestCase):
    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")

    def test_get_repo_map_all_languages(self):
        language_files = {
            "c": (
                "test.c",
                (
                    '#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n   '
                    " return 0;\n}\n"
                ),
            ),
            "csharp": (
                "test.cs",
                (
                    "using System;\n\nclass Program {\n    static void Main() {\n       "
                    ' Console.WriteLine("Hello, World!");\n    }\n}\n'
                ),
            ),
            "cpp": (
                "test.cpp",
                (
                    '#include <iostream>\n\nint main() {\n    std::cout << "Hello, World!" <<'
                    " std::endl;\n    return 0;\n}\n"
                ),
            ),
            "elisp": ("test.el", '(defun greet (name)\n  (message "Hello, %s!" name))\n'),
            "elixir": (
                "test.ex",
                (
                    'defmodule Greeter do\n  def hello(name) do\n    IO.puts("Hello, #{name}!")\n '
                    " end\nend\n"
                ),
            ),
            "elm": (
                "test.elm",
                (
                    "module Main exposing (main)\n\nimport Html exposing (text)\n\nmain =\n    text"
                    ' "Hello, World!"\n'
                ),
            ),
            "go": (
                "test.go",
                (
                    'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("Hello,'
                    ' World!")\n}\n'
                ),
            ),
            "java": (
                "Test.java",
                (
                    "public class Test {\n    public static void main(String[] args) {\n       "
                    ' System.out.println("Hello, World!");\n    }\n}\n'
                ),
            ),
            "javascript": (
                "test.js",
                "function greet(name) {\n    console.log(`Hello, ${name}!`);\n}\n",
            ),
            "ocaml": ("test.ml", 'let greet name =\n  Printf.printf "Hello, %s!\\n" name\n'),
            "php": (
                "test.php",
                '<?php\nfunction greet($name) {\n    echo "Hello, $name!";\n}\n?>\n',
            ),
            "python": ("test.py", 'def greet(name):\n    print(f"Hello, {name}!")\n'),
            "ql": ("test.ql", 'predicate greet(string name) {\n  name = "World"\n}\n'),
            "ruby": ("test.rb", 'def greet(name)\n  puts "Hello, #{name}!"\nend\n'),
            "rust": ("test.rs", 'fn main() {\n    println!("Hello, World!");\n}\n'),
            "typescript": (
                "test.ts",
                "function greet(name: string): void {\n    console.log(`Hello, ${name}!`);\n}\n",
            ),
            "tsx": (
                "test.tsx",
                (
                    "import React from 'react';\n\nconst Greeting: React.FC<{ name: string }> = ({"
                    " name }) => {\n    return <h1>Hello, {name}!</h1>;\n};\n\nexport default"
                    " Greeting;\n"
                ),
            ),
        }

        with IgnorantTemporaryDirectory() as temp_dir:
            for _, (filename, content) in language_files.items():
                with open(os.path.join(temp_dir, filename), "w") as f:
                    f.write(content)

            io = InputOutput()
            repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
            other_files = [
                os.path.join(temp_dir, filename) for filename, _ in language_files.values()
            ]
            result = repo_map.get_repo_map([], other_files)

            # Check if the result contains all the expected files
            for lang, (filename, _) in language_files.items():
                self.assertIn(filename, result, f"File for language {lang} not found in repo map")

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
