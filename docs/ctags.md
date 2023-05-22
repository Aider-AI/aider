
# Improving GPT-4's codebase understanding with ctags

While GPT-4 excels at coding tasks, it struggles with modifying
code in larger code bases.
Many common
types of code changes require knowledge and context from multiple files
scattered throughout a large repo. 
This is a challenge for GPT-4, which can only fit 8k-tokens
worth of code in its context window.

To address this issue, `aider` has
a new experimental feature that utilizes `ctags` to provide
GPT with a **concise map of the whole repository** including
all declared variables and functions with call signatures.
This *repo map* enables GPT to better comprehend, navigate
and edit the code in larger repos.

## The problem: code context

GPT-4 is great at "self contained" coding tasks, like writing or
modifying a pure function with no external dependencies. These work
well because you can send GPT a self-contained request ("write a
Fibonacci function") and it can create new code from whole cloth. Or
you can send it an existing function implementation and ask for self-contained
changes ("rewrite the loop using list
comprehensions"). These require no context beyond the code being
discussed.

Most real code is not pure and self-contained. And many common code
changes require you to understand related code from many different files in a
repo.  If you want GPT to "switch all the print statements in Foo to
use the logging system", it needs to see the code in the Foo class
with the prints, and it also needs to understand how the project's logging
system works.

A simple solution is to **send the entire codebase** to GPT along with
each change request. Now GPT has all the context! But even moderately
sized repos won't fit in the 8k-token context window. An
improved approach is to be selective, and **hand pick which files to send**.
For the example above, you could send the file that
contains Foo and the file that contains the logging subsystem.

This works pretty well, and is how `aider` previously worked. You
manually specify which files to "add to the chat".

But it's not ideal to have to manually identify and curate the right
set of files to add to the chat. It can get complicated, as
some changes will need context from many files. And you might still overrun
the context window if you need to add too many files for context,
many of which aren't going to end up being modified.

## Using a repo map to provide context

The latest version of `aider` sends a **repo map** to GPT along with
each change request. The map contains a list of all the files in the
repo, along with the symbols which are defined in each file. Callables
like functions and methods also include their signatures. Here's a
piece of the map of the aider repo, just mapping the
[main.py](https://github.com/paul-gauthier/aider/blob/main/aider/main.py) file:

```
aider/
   ...
   main.py:
      function
        main (args=None, input=None, output=None)
      variable
        status
```

Mapping out the repo like this provides some benefits:

  - GPT can see variables, classes, methods and function signatures from everywhere in the repo. This alone may give it enough context to solve many tasks. For example, it can probably figure out how to use the API exported from a module just based on the details shown in the map.
  - If it needs to see more code, GPT can use the map to figure out by itself which files it needs to look at. GPT will then ask to see these specific files, and `aider` will automatically add them to the chat context (with user approval).

Of course, for large repositories, even just their map might be too large
for the context window.  However, this mapping approach opens up the
ability to collaborate with GPT-4 on larger codebases than previous
methods.  It also reduces the need to manually curate which files to
add to the chat context, empowering GPT to autonomously identify
relevant files for the task at hand.

## Using ctags to make the map

Under the hood, `aider` uses
[universal ctags](https://github.com/universal-ctags/ctags)
to build the
map. Universal ctags can scan source code written in a large variety of
languages, and extract data about all the symbols defined in each
file.

For example, here is the `ctags --fields=+S --output-format=json` output for the `main.py` file mapped above:

```json
{
  "_type": "tag",
  "name": "main",
  "path": "aider/main.py",
  "pattern": "/^def main(args=None, input=None, output=None):$/",
  "kind": "function",
  "signature": "(args=None, input=None, output=None)"
}
{
  "_type": "tag",
  "name": "status",
  "path": "aider/main.py",
  "pattern": "/^    status = main()$/",
  "kind": "variable"
}
```

The repo map is built using the `name`, `path`, `scope`, `kind` and
`signature` data from `ctags`.
Rather then sending the data to GPT in that chatty json format, `aider`
formats the map as a sorted,
hierarchical tree. This is a format that GPT can easily understand and which efficiently conveys the map data to GPT-4 using a
minimal number of tokens.

## Example chat transcript

This
[chat transcript](https://aider.chat/examples/add-test.html)
shows GPT-4 creating a black box test case, **without being given
access to the source code of the function being tested or any of the
other code in the repo.**

Instead, GPT is operating solely off 
the repo map.
Using only the meta-data in the map, GPT is able to:

  - Find the function signature of the `cmd_add()` function which the user wants a test case for.
  - Determine that it is a method of the `Command` class, so the test case will need to instantiate an instance to conduct the test.
  - Identify that creating a `Command` instance requires passing in `InputOutput` and `Coder` instances.
  - Figure out the arguments required to instantiate the `InputOuput` instance.
  - Decide that the `Coder` class looks complex enough to use a `MagickMock`.


It makes one reasonable mistake in the first version of the test, but is
able to quickly fix the issue after being shown the `pytest` error output.

## Try it out

To use this experimental repo map feature:

  - Install [aider](https://github.com/paul-gauthier/aider#installation).
  - Install [universal ctags](https://github.com/universal-ctags/ctags).
  - Run `aider` with the `--ctags` option inside your repo.
  