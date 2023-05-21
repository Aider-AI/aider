
# Using ctags to help GPT-4 understand an entire repo

GPT-4 is great at coding, but it's hard to work with it to make
modifications inside a large code base.
GPT can't really understand and navigate more code than can fit
in its context window.
And many
common types of code changes will need knowledge and context from
multiple files strewn about the repo.
A new experimental feature of `aider` uses `ctags` to give GPT a
**repo map**, so that it can better understand and navigate larger repos.

## The problem: code context

GPT-4 is great at "self contained" coding tasks, like writing or
modifying a pure function with no external dependencies. These work
great because you can send GPT a self-contained request ("write a
Fibonacci function") and it can create new code from whole cloth. Or
you can send it an existing function implementation and ask for self
contained changes ("rewrite the loop using list
comprehensions"). These require no context beyond the code being
discussed.

Most real code is not pure and self-contained. And many common code
changes require you to understand many parts of the repo and relevant
external libraries. If you want GPT to "switch all the print
statements in Foo to use the logging system", it needs to see the code
in Foo with the prints, and it also needs to understand how the
logging system works.

A simple solution is to send the **entire codebase** to GPT along with
each change request. Now GPT has all the context! But even moderately
sized repos won't fit in the 8k-token GPT-4 context window. An
improvement is to be selective, and hand pick which files from the
repo to send. For the example above, you could send the file that
contains Foo and the file that contains the logging subsystem.

This works pretty well, and is how `aider` previously worked. You
manually specify which files to "add to the chat".

But it's not ideal to have to manually identify and curate the right
set of files to add to the chat. It can get complicated, as
some changes will need context from many files. And you might still overrun
the context window if individual files are very large.

## Using a repo map to provide context

The latest version of `aider` sends a **repo map** to GPT along with
each change request. The map contains a list of all the files in the
repo, along with the symbols which are defined in each file. Callables
like functions and methods also include their signatures. Here's a
piece of the map for the aider repo, just for
[main.py](https://github.com/paul-gauthier/aider/blob/main/aider/main.py):

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

  - GPT can see the variables, classes, methods and function signatures from everywhere in the repo. This alone may give it enough context to solve many tasks. For example, it can probably figure out how to use the API exported from a module based on the details shown in the map.
  - If it needs to see more code, GPT can use the map to figure out by itself which files it needs to look at. GPT will then ask to see these specific files, and `aider` will automatically add them to the chat context (with user approval).

Of course, for large repositories, even their map might be too large
for the context window.  However, this mapping approach opens up the
ability to collaborate with GPT-4 on larger codebases than previous
methods.  It also minimizes the need for manual curation of files to
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
`signature` data from `ctags`. The map is formatted as a sorted,
hierarchical tree to efficiently convey the data to GPT-4 using a
minimal number of tokens.

## Try it out

To use this experimental repo map feature with `aider`:

  - Install [universal ctags](https://github.com/universal-ctags/ctags).
  - Run `aider` with the `--ctags` option.
  