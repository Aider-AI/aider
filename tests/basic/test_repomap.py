import os
import unittest

from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.models import Model
from aider.repomap import RepoMap
from aider.utils import IgnorantTemporaryDirectory


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
            "ocaml": ("test.ml", "let greet name =\n  Printf.printf \"Hello, %s!\\n\" name\n"),
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


if __name__ == "__main__":
    unittest.main()
