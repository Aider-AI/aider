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
                "main",  # Key symbol to check
            ),
            "cpp": (
                "test.cpp",
                (
                    '#include <iostream>\n\nint main() {\n    std::cout << "Hello, World!" <<'
                    " std::endl;\n    return 0;\n}\n"
                ),
                "main",  # Key symbol to check
            ),
            "elixir": (
                "test.ex",
                (
                    'defmodule Greeter do\n  def hello(name) do\n    IO.puts("Hello, #{name}!")\n '
                    " end\nend\n"
                ),
                "Greeter",  # Key symbol to check
            ),
            "java": (
                "Test.java",
                """public interface Greeting {
    String greet(String name);
}

public class Test implements Greeting {
    private String prefix = "Hello";

    public String greet(String name) {
        return prefix + ", " + name + "!";
    }

    public static void main(String[] args) {
        Test greeter = new Test();
        System.out.println(greeter.greet("World"));
    }
}
""",
                "Greeting",  # Key symbol to check
            ),
            "javascript": (
                "test.js",
                """// Class definition
class Person {
    constructor(name) {
        this.name = name;
    }

    sayHello() {
        return `Hello, ${this.name}!`;
    }
}

// Function declaration
function greet(person) {
    return person.sayHello();
}

// Variables and constants
const DEFAULT_NAME = 'World';
let currentPerson = new Person(DEFAULT_NAME);

// Export for use in other modules
module.exports = {
    Person,
    greet,
    DEFAULT_NAME
};
""",
                "Person",  # Key symbol to check
            ),
            "ocaml": (
                "test.ml",
                """(* Module definition *)
module Greeter = struct
  type person = {
    name: string;
    age: int
  }

  let create_person name age =
    {name; age}

  let greet person =
    Printf.printf "Hello, %s! You are %d years old.\\n"
      person.name person.age
end

(* Outside the module *)
let () =
  let person = Greeter.create_person "Alice" 30 in
  Greeter.greet person
""",
                "Greeter",  # Key symbol to check
            ),
            "php": (
                "test.php",
                '<?php\nfunction greet($name) {\n    echo "Hello, $name!";\n}\n?>\n',
                "greet",  # Key symbol to check
            ),
            "python": (
                "test.py",
                '''from typing import Optional, List

class Person:
    """A class representing a person."""

    def __init__(self, name: str, age: Optional[int] = None):
        self.name = name
        self.age = age

    def greet(self, formal: bool = False) -> str:
        """Generate a greeting."""
        prefix = "Good day" if formal else "Hello"
        return f"{prefix}, {self.name}!"

def create_greeting_list(people: List[Person]) -> List[str]:
    """Create greetings for a list of people."""
    return [person.greet() for person in people]

# Constants
DEFAULT_NAME = "World"
MAX_AGE = 150

if __name__ == "__main__":
    person = Person(DEFAULT_NAME)
    print(person.greet())
''',
                "Person",  # Key symbol to check
            ),
            "ql": (
                "test.ql",
                'predicate greet(string name) {\n  name = "World"\n}\n',
                "greet",  # Key symbol to check
            ),
            "ruby": (
                "test.rb",
                'def greet(name)\n  puts "Hello, #{name}!"\nend\n',
                "greet",  # Key symbol to check
            ),
            "rust": (
                "test.rs",
                """// Define a trait
trait Greeting {
    fn greet(&self) -> String;
}

// Define a struct
struct Person {
    name: String,
    age: u32,
}

// Implement the trait for Person
impl Greeting for Person {
    fn greet(&self) -> String {
        format!("Hello, {}! You are {} years old.", self.name, self.age)
    }
}

// Implementation block for Person
impl Person {
    fn new(name: String, age: u32) -> Self {
        Person { name, age }
    }
}

// Constants
const DEFAULT_NAME: &str = "World";
const MAX_AGE: u32 = 150;

fn main() {
    let person = Person::new(DEFAULT_NAME.to_string(), 30);
    println!("{}", person.greet());
}
""",
                "Person",  # Key symbol to check
            ),
            "typescript": (
                "test.ts",
                "function greet(name: string): void {\n    console.log(`Hello, ${name}!`);\n}\n",
                "greet",  # Key symbol to check
            ),
            "tsx": (
                "test.tsx",
                """import React, { useState, useEffect } from 'react';

interface UserProps {
    name: string;
    age?: number;
}

// Component with props interface
const UserGreeting: React.FC<UserProps> = ({ name, age }) => {
    const [greeting, setGreeting] = useState<string>('');

    useEffect(() => {
        setGreeting(`Hello, ${name}${age ? ` (${age})` : ''}!`);
    }, [name, age]);

    return <h1>{greeting}</h1>;
};

// Custom hook
function useCounter(initial: number = 0) {
    const [count, setCount] = useState(initial);
    const increment = () => setCount(c => c + 1);
    return { count, increment };
}

// Constants
const DEFAULT_NAME = 'World';
const MAX_AGE = 150;

export { UserGreeting, useCounter, DEFAULT_NAME, MAX_AGE };
""",
                "UserProps",  # Key symbol to check
            ),
            "csharp": (
                "test.cs",
                """using System;
using System.Collections.Generic;

namespace Greetings {
    public interface IGreeter {
        string Greet(string name);
    }

    public class Person {
        public string Name { get; set; }
        public int Age { get; set; }

        public Person(string name, int age) {
            Name = name;
            Age = age;
        }
    }

    public class FormalGreeter : IGreeter {
        private const string PREFIX = "Good day";
        private static readonly int MAX_AGE = 150;

        public string Greet(string name) {
            return $"{PREFIX}, {name}!";
        }

        public string GreetPerson(Person person) {
            return $"{PREFIX}, {person.Name} ({person.Age})!";
        }
    }

    public class Program {
        static void Main() {
            var greeter = new FormalGreeter();
            var person = new Person("World", 42);
            Console.WriteLine(greeter.GreetPerson(person));
        }
    }
}""",
                "IGreeter",  # Key symbol to check
            ),
            ##################### FIX ALL THE ONES BELOW HERE vvvvvvvvvvv
            "elisp": (
                "test.el",
                """(defvar *default-greeting* "Hello")
(defvar *max-name-length* 50)

(defstruct person
  (name "Anonymous")
  (age 0))

(defclass greeter ()
  ((prefix :initarg :prefix
           :accessor greeter-prefix
           :initform *default-greeting*)))

(defmethod greet ((g greeter) (p person))
  (format nil "~A, ~A! You are ~D years old."
          (greeter-prefix g)
          (person-name p)
          (person-age p)))

(defun create-formal-greeter ()
  (make-instance 'greeter :prefix "Good day"))

(defun main ()
  (let ((greeter (create-formal-greeter))
        (person (make-person :name "World" :age 42)))
    (message "%s" (greet greeter person))))""",
                "greeter",  # Key symbol to check
            ),
            "elm": (
                "test.elm",
                """module Main exposing (main, Person, Greeting)

import Html exposing (Html, div, text)
import Html.Attributes exposing (class)

type alias Person =
    { name : String
    , age : Int
    }

type Greeting
    = Formal
    | Casual

greet : Greeting -> Person -> String
greet style person =
    let
        prefix =
            case style of
                Formal ->
                    "Good day"
                
                Casual ->
                    "Hi"
    in
    prefix ++ ", " ++ person.name ++ "!"

defaultPerson : Person
defaultPerson =
    { name = "World"
    , age = 42
    }

main : Html msg
main =
    div [ class "greeting" ]
        [ text (greet Formal defaultPerson)
        ]""",
                "Person",  # Key symbol to check
            ),
            "go": (
                "test.go",
                """package main

import (
    "fmt"
    "strings"
)

// Person represents someone who can be greeted
type Person struct {
    Name string
    Age  int
}

// Greeter defines greeting behavior
type Greeter interface {
    Greet(p Person) string
}

// FormalGreeter implements Greeter with formal style
type FormalGreeter struct {
    Prefix string
}

const (
    DefaultName = "World"
    MaxAge     = 150
)

func (g FormalGreeter) Greet(p Person) string {
    return fmt.Sprintf("%s, %s! You are %d years old.", 
        g.Prefix, p.Name, p.Age)
}

func NewFormalGreeter() *FormalGreeter {
    return &FormalGreeter{Prefix: "Good day"}
}

func main() {
    greeter := NewFormalGreeter()
    person := Person{Name: DefaultName, Age: 42}
    fmt.Println(greeter.Greet(person))
}""",
                "Greeter",  # Key symbol to check
            ),
            "dart": (
                "test.dart",
                """abstract class Greeting {
  String greet(Person person);
}

class Person {
  final String name;
  final int age;
  
  const Person(this.name, this.age);
}

class FormalGreeting implements Greeting {
  static const String prefix = 'Good day';
  static const int maxAge = 150;
  
  @override
  String greet(Person person) {
    return '$prefix, ${person.name}! You are ${person.age} years old.';
  }
}

void main() {
  final greeter = FormalGreeting();
  final person = Person('World', 42);
  print(greeter.greet(person));
}""",
                "Greeting",  # Key symbol to check
            ),
        }

        for lang, (filename, content, key_symbol) in language_files.items():
            with GitTemporaryDirectory() as temp_dir:
                with open(os.path.join(temp_dir, filename), "w") as f:
                    f.write(content)

                io = InputOutput()
                repo_map = RepoMap(main_model=self.GPT35, root=temp_dir, io=io)
                other_files = [filename]
                result = repo_map.get_repo_map([], other_files)
                dump(lang)
                dump(result)

                self.assertGreater(len(result.strip().splitlines()), 1)

                # Check if the result contains all the expected files and symbols
                self.assertIn(
                    filename, result, f"File for language {lang} not found in repo map: {result}"
                )
                self.assertIn(
                    key_symbol,
                    result,
                    (
                        f"Key symbol '{key_symbol}' for language {lang} not found in repo map:"
                        f" {result}"
                    ),
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
