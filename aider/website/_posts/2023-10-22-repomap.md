---
title: Building a better repository map with tree sitter
excerpt: Tree-sitter allows aider to build a repo map that better summarizes large code bases.
highlight_image: /assets/robot-ast.png
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Building a better repository map with tree sitter

![robot flowchat](/assets/robot-ast.png)

GPT-4 is extremely useful for "self-contained" coding tasks,
like generating or modifying a simple function
that has no dependencies. Tools like GitHub CoPilot serve
these simple coding tasks well.

But making complex changes in a larger, pre-existing codebase
is much more difficult, for both humans and AIs.
To do this successfully, you need to:

1. Find the code that needs to be changed.
2. Understand how that code relates to the rest of the codebase.
3. Make the correct code change to accomplish the task.

GPT-4 is actually great at making the code changes (3),
once you tell it which files need to be changed (1)
and show it how they fit into the rest of the codebase (2).

This article is going to focus on step (2), providing "code context":

  - We need to help GPT understand the overall codebase.
  - This will help it understand the code it needs to change, which may depend on other parts of the codebase.
  - It will also help GPT write new code and modify the existing code in a way
that respects and utilizes existing libraries, modules and abstractions
found elsewhere in the codebase.
  - We must convey all of this "code context" to GPT in an
efficient manner that fits within the limited context window.

To address these issues, aider
sends GPT a **concise map of your whole git repository**
that includes
the most important classes and functions along with their types and call signatures.

This **repository map** is now built automatically using
[tree-sitter](https://tree-sitter.github.io/tree-sitter/)
to extract symbol definitions from source files.
Tree-sitter is used by many IDEs, editors and LSP servers to
help humans search and navigate large codebases.
Aider now uses it to help GPT better comprehend, navigate
and edit code in larger repos.

*To code with GPT-4 using the techniques discussed here, just install [aider](https://aider.chat/docs/install.html).*


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
use the BarLog logging system", it needs to see and
modify the code in the Foo class, but it also needs to understand
how to use
the project's BarLog
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
This works pretty well, and is supported by aider -- you
can manually specify which files to "add to the chat" you are having with GPT.

But sending whole files is a bulky way to send code context,
wasting the precious context window.
GPT doesn't need to see the entire implementation of BarLog,
it just needs to understand it well enough to use it.
You may quickly run out of context window by sending
full files of code
just to convey context.

Aider also strives to reduce the manual work involved in
coding with AI.
So in an ideal world, we'd like aider to automatically
identify and provide the needed code context.

## Using a repo map to provide context

Aider sends a **repo map** to GPT along with
each request from the user to make a code change.
The map contains a list of the files in the
repo, along with the key symbols which are defined in each file.
It shows how each of these symbols are defined in the
source code, by including the critical lines of code for each definition.

Here's a
sample of the map of the aider repo, just showing the maps of
[base_coder.py](https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py)
and
[commands.py](https://github.com/Aider-AI/aider/blob/main/aider/commands.py)
:

```
aider/coders/base_coder.py:
⋮...
│class Coder:
│    abs_fnames = None
⋮...
│    @classmethod
│    def create(
│        self,
│        main_model,
│        edit_format,
│        io,
│        skip_model_availabily_check=False,
│        **kwargs,
⋮...
│    def abs_root_path(self, path):
⋮...
│    def run(self, with_message=None):
⋮...

aider/commands.py:
⋮...
│class Commands:
│    voice = None
│
⋮...
│    def get_commands(self):
⋮...
│    def get_command_completions(self, cmd_name, partial):
⋮...
│    def run(self, inp):
⋮...
```

Mapping out the repo like this provides some key benefits:

  - GPT can see classes, methods and function signatures from everywhere in the repo. This alone may give it enough context to solve many tasks. For example, it can probably figure out how to use the API exported from a module just based on the details shown in the map.
  - If it needs to see more code, GPT can use the map to figure out by itself which files it needs to look at in more detail. GPT will then ask to see these specific files, and aider will automatically add them to the chat context.

## Optimizing the map

Of course, for large repositories even just the repo map might be too large
for GPT's context window.
Aider solves this problem by sending just the **most relevant**
portions of the repo map.
It does this by analyzing the full repo map using
a graph ranking algorithm, computed on a graph
where each source file is a node and edges connect
files which have dependencies.
Aider optimizes the repo map by
selecting the most important parts of the codebase
which will
fit into the token budget assigned by the user
(via the `--map-tokens` switch, which defaults to 1k tokens).

The sample map shown above doesn't contain *every* class, method and function from those
files.
It only includes the most important identifiers,
the ones which are most often referenced by other portions of the code.
These are the key pieces of context that GPT needs to know to understand
the overall codebase.


## Using tree-sitter to make the map

Under the hood, aider uses
[tree sitter](https://tree-sitter.github.io/tree-sitter/)
to build the
map.
It specifically uses the
[py-tree-sitter-languages](https://github.com/grantjenks/py-tree-sitter-languages)
python module,
which provides simple, pip-installable binary wheels for
[most popular programming languages](https://github.com/Aider-AI/grep-ast/blob/main/grep_ast/parsers.py).

Tree-sitter parses source code into an Abstract Syntax Tree (AST) based
on the syntax of the programming language.
Using the AST, we can identify where functions, classes, variables, types and
other definitions occur in the source code.
We can also identify where else in the code these things are used or referenced.

Aider uses all of these definitions and references to
determine which are the most important identifiers in the repository,
and to produce the repo map that shows just those key
lines from the codebase.

## What about ctags?

The tree-sitter repository map replaces the
[ctags based map](https://aider.chat/docs/ctags.html)
that aider originally used.
Switching from ctags to tree-sitter provides a bunch of benefits:

- The map is richer, showing full function call signatures and other details straight from the source files.
- Thanks to `py-tree-sitter-languages`, we get full support for many programming languages via a python package that's automatically installed as part of the normal `python -m pip install -U aider-chat`.
- We remove the requirement for users to manually install `universal-ctags` via some external tool or package manager (brew, apt, choco, etc).
- Tree-sitter integration is a key enabler for future work and capabilities for aider.

## Future work

You'll recall that we identified the 3 key steps
required to use GPT
to complete a coding task within a large, pre-existing codebase:

1. Find the code that needs to be changed.
2. Understand how that code relates to the rest of the codebase.
3. Make the correct code change to accomplish the task.

We're now using tree-sitter to help solve the code context problem (2),
but it's also an important foundation
for future work on automatically finding all the code which
will need to be changed (1).

Right now, aider relies on the user to specify which source files
will need to be modified to complete their request.
Users manually "add files to the chat" using aider's `/add` command,
which makes those files available for GPT to modify.

This works well, but a key piece of future work is to harness the
power of GPT and tree-sitter to automatically identify
which parts of the code will need changes.

## Try it out

To code with GPT-4 using the techniques discussed here,
just install [aider](https://aider.chat/docs/install.html).

## Credits

Aider uses
[modified versions of the tags.scm files](https://github.com/Aider-AI/aider/tree/main/aider/queries)
from these
open source tree-sitter language implementations:

* [https://github.com/tree-sitter/tree-sitter-c](https://github.com/tree-sitter/tree-sitter-c) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-c-sharp](https://github.com/tree-sitter/tree-sitter-c-sharp) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-cpp](https://github.com/tree-sitter/tree-sitter-cpp) — licensed under the MIT License.
* [https://github.com/Wilfred/tree-sitter-elisp](https://github.com/Wilfred/tree-sitter-elisp) — licensed under the MIT License.
* [https://github.com/elixir-lang/tree-sitter-elixir](https://github.com/elixir-lang/tree-sitter-elixir) — licensed under the Apache License, Version 2.0.
* [https://github.com/elm-tooling/tree-sitter-elm](https://github.com/elm-tooling/tree-sitter-elm) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-go](https://github.com/tree-sitter/tree-sitter-go) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-java](https://github.com/tree-sitter/tree-sitter-java) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-javascript](https://github.com/tree-sitter/tree-sitter-javascript) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-ocaml](https://github.com/tree-sitter/tree-sitter-ocaml) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-php](https://github.com/tree-sitter/tree-sitter-php) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-python](https://github.com/tree-sitter/tree-sitter-python) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-ql](https://github.com/tree-sitter/tree-sitter-ql) — licensed under the MIT License.
* [https://github.com/r-lib/tree-sitter-r](https://github.com/r-lib/tree-sitter-r) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-ruby](https://github.com/tree-sitter/tree-sitter-ruby) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-rust](https://github.com/tree-sitter/tree-sitter-rust) — licensed under the MIT License.
* [https://github.com/tree-sitter/tree-sitter-typescript](https://github.com/tree-sitter/tree-sitter-typescript) — licensed under the MIT License.
