
* Using ctags to help GPT-4 understand an entire repo

Coding with GPT-4 against large code bases has been difficult. It's hard for GPT to understand a large codebase well enough to make many common types of code changes that need knowledge and context from multiple files. A new feature of `aider` uses `ctags` to give GPT a map of the repo so it can better understand and navigate larger repos.

** The problem of code context

GPT-4 is great at "self contained" coding tasks, like writing or modifying a pure function with no external dependencies. These work great because you send GPT a self-contained question ("write a Fibonacci function") and it can create new code from whole cloth. Or you can send it an existing function implementation and ask for self contained changes ("rewrite the loop using list comprehensions"). These require no context beyond the code being discussed.

Most real code is not pure and self-contained. To understand and modify such code, you need to understand the rest of the repo and relevant external libraries. If you ask GPT to "switch all the print statements in Foo to use the logging system", it needs to see the code with the prints and also needs to understand how the logging system works.

A simple solution is to send the entire codebase to GPT along with every change request. Now GPT has all the context! But even moderately sized projects won't all fit in the 8K GPT-4 context window. An improvement is to be selective, and hand pick which parts of the repo to send with each request. For the example above, you could send the source file that contains Foo and the file that contains the logging subsystem.

This works well, and is how `aider` previously worked. You manually choose which files to "add to the chat".

But it's not ideal to have to manually identify and curate the right subset of the code base for each change request. It can get complicated, as some requests need context from many files. You may still overrun the context window.

** Using a repo map as context

The latest version of `aider` sends a "map" of the repo to GPT. The map contains a list of all the files in the repo, along with the symbols which are defined in each file. Callables like functions and methods also include their signature. Here's a piece of the map for [main.py](https://github.com/paul-gauthier/aider/blob/main/aider/main.py) from the `aider` repo:

```
aider/
   main.py:
      function
        main (args=None, input=None, output=None)
      variable
        status
```

Mapping out the entire repo like this provides a number of benefits:

  - GPT can see the variables, classes, methods and function signatures from everywhere in the repo. This alone may give it enough context to solve many tasks. For example, it can probably figure out how to use the API exported from a module from this map.
  - If it needs to see more code, GPT use the map to figure out which files it needs to look at. It can ask to see these files, and `aider` will automatically add them to the chat context (with user approval).

Of course, large repos will have maps that are too large for the context window. But this mapping approach makes it possible to collaborate with GPT-4 on larger code bases than was possible before. And it reduces the need to manually curate which files need to be added to the chat for context.

** Using ctags to make the map

Under the hood, `aider` uses the [universal ctags](https://github.com/universal-ctags/ctags) tool to build the map. Universal ctags can scan source code in a large variety of languages, and extract data about all the symbols defined in each file.

For example, here is the `ctags` output for the `main.py` mapped above:

```json
$ ctags --fields=+S --output-format=json aider/main.py | jq

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

Aider uses the `name`, `path`, `scope`, `kind` and `signature` data to create the map. It sorts and reformats the map into a hierarchical representation to efficiently convey the data using a minimal number of tokens.
