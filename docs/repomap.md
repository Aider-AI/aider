
# Building a better repository map with tree sitter

![robot flowchat](../assets/robot-ast.png)

GPT-4 is extremely useful for "self-contained" coding tasks,
like generating brand new code or modifying a pure function
that has no dependencies. Tools like GitHub CoPilot serve this
task well, by "autocompleting" a stand alone function.

But it's difficult to use GPT-4 to work within
a large, complex pre-existing codebase.
Accomplishing a programming task in a large codebase presents
two problems:

1. Identifying which parts of the codebase need to be modified to complete the task.
2. Understanding the dependencies and APIs which interconnect the codebase, so that the modifications can make use of existing abstractions, tools, libraries, submodules, etc.

We'll be discussing the second problem in this article, the problem of "code context".
We need to:

  - Help GPT understand the overall codebase, so that it
can decifer the meaning of code with complex dependencies and generate
new code that respects and utilizes existing abstractions.
  - Convey all of this "code context" to GPT in an
efficient manner that fits within GPT's context window.

To address these issues, aider
sends GPT a **concise map of your whole git repository**
that includes
the most important classes and functions along with their types and call signatures.
This *repository map* is built automatically using `tree-sitter`, which
extracts symbol definitions from source files.
Tree-sitter is used by many IDEs and editors (and LSP servers) to
help humans search and navigate large codebases.
Instead, we're going to use it to help GPT better comprehend, navigate
and edit code in larger repos.

To code with GPT-4 using the techniques discussed here,
just install [aider](https://aider.chat/docs/install.html).

## The problem: code context

GPT-4 is great at "self contained" coding tasks, like writing or
modifying a pure function with no external dependencies.
GPT can easily handle requests like "write a
Fibonacci function" or "rewrite this loop using list
comprehensions", because they require no context beyond the code
being discussed.

Most real code is not pure and self-contained, it is intertwined with
and depends on code from many different files in a repo.
If you ask GPT to "switch all the print statements in class Foo to
use the BarLog logging system", it needs to see the code in the Foo class
with the prints, and it also needs to understand the project's BarLog
subsystem.

A simple solution is to **send the entire codebase** to GPT along with
each change request. Now GPT has all the context! But this won't work
for even moderately
sized repos, because they won't fit into the context window.

A better approach is to be selective,
and **hand pick which files to send**.
For the example above, you could send the file that
contains the Foo class
and the file that contains the BarLog logging subsystem.
This works pretty well, and is supported by `aider` -- you
can manually specify which files to "add to the chat" you are having with GPT.

But sending whole files is a bulky way to send code context,
wasting the precious context window.
GPT doesn't need to see the entire implementation of BarLog,
it just needs to understand it well enough to use it.
You may quickly run out of context window if you
send many files worth of code just to convey context.

## Using a repo map to provide context

Aider sends a **repo map** to GPT along with
each change request. The map contains a list of the files in the
repo, along with the key symbols which are defined in each file. Callables
like functions and methods also include their types and signatures.

Here's a
sample of the map of the aider repo, just showing the maps of
[io.py](https://github.com/paul-gauthier/aider/blob/main/aider/io.py)
and
[main.py](https://github.com/paul-gauthier/aider/blob/main/aider/main.py)
:

```
aider/io.py:
⋮...
│class InputOutput:
│    num_error_outputs = 0
⋮...
│    def read_text(self, filename):
⋮...
│    def write_text(self, filename, content):
⋮...
│    def confirm_ask(self, question, default="y"):
⋮...
│    def tool_error(self, message):
⋮...
│    def tool_output(self, *messages, log_only=False):
⋮...

aider/main.py:
⋮...
│def main(argv=None, input=None, output=None, force_git_root=None):
⋮...
```

Mapping out the repo like this provides some key benefits:

  - GPT can see classes, methods and function signatures from everywhere in the repo. This alone may give it enough context to solve many tasks. For example, it can probably figure out how to use the API exported from a module just based on the details shown in the map.
  - If it needs to see more code, GPT can use the map to figure out by itself which files it needs to look at. GPT will then ask to see these specific files, and `aider` will automatically add them to the chat context (with user approval).

Of course, for large repositories even just the repo map might be too large
for the context window.
Aider solves this problem by analyzing the full repo map using
a graph ranking algorithm.
By examining which files reference classes and functions in other files,
aider can determine the most important portions of the repo map.
Aider builds the repo map by
selecting the most important parts of the codebase
which will
fit into the token budget assigned by the user
(via the `--map-tokens` switch, which defaults to 1k tokens).


## Using tree-sitter to make the map

Under the hood, aider uses
[tree sitter](https://tree-sitter.github.io/tree-sitter/)
to build the
map.
It specifically uses the
[py-tree-sitter-languages](https://github.com/grantjenks/py-tree-sitter-languages)
python module,
which provides simple, pip-installable binary wheels for
[most popular programming languages](https://github.com/paul-gauthier/grep-ast/blob/main/grep_ast/parsers.py).

Tree-sitter parses source code into an Abstract Syntax Tree,
which structures the plain text in the source file into a tree, based
on the syntax of the programming language.
Using the AST, we can identify where functions, classes, variables, types and
other definitions occur in the source code.
We can also identify where else in the code these things are used or referenced.

Aider uses all of these definitions and references to
determine which are the most important identifiers in the repository,
and to produce the repo map that shows just those key
lines from the codebase.

## Future work

You'll recall that we identified two key challenges when trying to use GPT
to code within a large, pre-existing codebase:

1. Identifying which parts of the codebase need to be modified to complete the task.
2. Understanding the dependencies and APIs which interconnect the codebase, so that the modifications can make use of existing abstractions, tools, libraries, submodules, etc.

The repo-map is a solution to the second problem.
One key reason for adopting tree-sitter to build the repo-map is
to lay the foundation for future work to solve the first problem.

Right now, aider relies on the user to specify which source files
will need to be modified to complete their request.
Users manually "add files to the chat" using aider's `/add` command,
and those files are available for GPT to modify.

This works well, but a key piece of future work is to harness the
power of GPT and tree-sitter to automatically identify
which parts of the code will need changes.

## Try it out

To code with GPT-4 using the techniques discussed here,
just install [aider](https://aider.chat/docs/install.html).


## Credits

Aider uses
[modified versions of the `tags.scm` files](https://github.com/paul-gauthier/aider/tree/main/aider/queries)
from these
open source tree-sitter language implementations:

* https://github.com/Wilfred/tree-sitter-elisp — licensed under the MIT License.
* https://github.com/camdencheek/tree-sitter-go-mod — licensed under the MIT License.
* https://github.com/elixir-lang/tree-sitter-elixir — licensed under the Apache License, Version 2.0.
* https://github.com/elm-tooling/tree-sitter-elm — licensed under the MIT License.
* https://github.com/r-lib/tree-sitter-r — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-c-sharp — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-cpp — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-go — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-java — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-javascript — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-ocaml — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-php — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-python — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-ql — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-ruby — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-rust — licensed under the MIT License.
* https://github.com/tree-sitter/tree-sitter-typescript — licensed under the MIT License.
