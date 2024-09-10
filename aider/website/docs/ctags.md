---
title: Improving GPT-4's codebase understanding with ctags
excerpt: Using ctags to build a "repository map" to increase GPT-4's ability to understand a large code base.
highlight_image: /assets/robot-flowchart.png
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Improving GPT-4's codebase understanding with ctags

![robot flowchat](/assets/robot-flowchart.png)


## Updated

Aider no longer uses ctags to build a repo map.
Please see the newer article about
[using tree-sitter to build a better repo map](https://aider.chat/docs/repomap.html).

-------

GPT-4 is extremely useful for "self-contained" coding tasks,
like generating brand new code or modifying a pure function
that has no dependencies.

But it's difficult to use GPT-4 to modify or extend
a large, complex pre-existing codebase.
To modify such code, GPT needs to understand the dependencies and APIs
which interconnect its subsystems.
Somehow we need to provide this "code context" to GPT
when we ask it to accomplish a coding task. Specifically, we need to:

  - Help GPT understand the overall codebase, so that it
can decifer the meaning of code with complex dependencies and generate
new code that respects and utilizes existing abstractions.
  - Convey all of this "code context" to GPT in an
efficient manner that fits within the 8k-token context window.

To address these issues, `aider` now
sends GPT a **concise map of your whole git repository**
that includes
all declared variables and functions with call signatures.
This *repo map* is built automatically using `ctags`, which
extracts symbol definitions from source files. Historically,
ctags were generated and indexed by IDEs and editors to
help humans search and navigate large codebases.
Instead, we're going to use ctags to help GPT better comprehend, navigate
and edit code in larger repos.

To get a sense of how effective this can be, this
[chat transcript](https://aider.chat/examples/add-test.html)
shows GPT-4 creating a black box test case, **without being given
access to the source code of the function being tested or any of the
other code in the repo.**
Using only the meta-data in the repo map, GPT is able to figure out how to
call the method to be tested, as well as how to instantiate multiple
class objects that are required to prepare for the test.

To code with GPT-4 using the techniques discussed here:


  - Install [aider](https://aider.chat/docs/install.html).
  - Install universal ctags.
  - Run `aider` inside your repo, and it should say "Repo-map: universal-ctags using 1024 tokens".

## The problem: code context

GPT-4 is great at "self contained" coding tasks, like writing or
modifying a pure function with no external dependencies.
GPT can easily handle requests like "write a
Fibonacci function" or "rewrite the loop using list
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
sized repos, because they won't fit into the 8k-token context window.

A better approach is to be selective,
and **hand pick which files to send**.
For the example above, you could send the file that
contains the Foo class
and the file that contains the BarLog logging subsystem.
This works pretty well, and is supported by `aider` -- you
can manually specify which files to "add to the chat" you are having with GPT.

But it's not ideal to have to manually identify the right
set of files to add to the chat.
And sending whole files is a bulky way to send code context,
wasting the precious 8k context window.
GPT doesn't need to see the entire implementation of BarLog,
it just needs to understand it well enough to use it.
You may quickly run out of context window if you
send many files worth of code just to convey context.

## Using a repo map to provide context

The latest version of `aider` sends a **repo map** to GPT along with
each change request. The map contains a list of all the files in the
repo, along with the symbols which are defined in each file. Callables
like functions and methods also include their signatures.

Here's a
sample of the map of the aider repo, just showing the maps of
[main.py](https://github.com/paul-gauthier/aider/blob/main/aider/main.py)
and
[io.py](https://github.com/paul-gauthier/aider/blob/main/aider/io.py)
:

```
aider/
   ...
   main.py:
      function
         main (args=None, input=None, output=None)
      variable
         status
   ...
   io.py:
      class
         FileContentCompleter
         InputOutput
      FileContentCompleter
         member
            __init__ (self, fnames, commands)
            get_completions (self, document, complete_event)
      InputOutput
         member
            __init__ (self, pretty, yes, input_history_file=None, chat_history_file=None, input=None, output=None)
            ai_output (self, content)
            append_chat_history (self, text, linebreak=False, blockquote=False)
            confirm_ask (self, question, default="y")
            get_input (self, fnames, commands)
            prompt_ask (self, question, default=None)
            tool (self, *messages, log_only=False)
            tool_error (self, message)
   ...
```

Mapping out the repo like this provides some benefits:

  - GPT can see variables, classes, methods and function signatures from everywhere in the repo. This alone may give it enough context to solve many tasks. For example, it can probably figure out how to use the API exported from a module just based on the details shown in the map.
  - If it needs to see more code, GPT can use the map to figure out by itself which files it needs to look at. GPT will then ask to see these specific files, and `aider` will automatically add them to the chat context (with user approval).

Of course, for large repositories even just the map might be too large
for the context window.  However, this mapping approach opens up the
ability to collaborate with GPT-4 on larger codebases than previous
methods.  It also reduces the need to manually curate which files to
add to the chat context, empowering GPT to autonomously identify
relevant files for the task at hand.

## Using ctags to make the map

Under the hood, `aider` uses
[universal ctags](https://github.com/universal-ctags/ctags)
to build the
map. Universal ctags can scan source code written in many
languages, and extract data about all the symbols defined in each
file.

Historically, ctags were generated and indexed by IDEs or code editors
to make it easier for a human to search and navigate a
codebase, find the implementation of functions, etc.
Instead, we're going to use ctags to help GPT navigate and understand the codebase.

Here is the type of output you get when you run ctags on source code. Specifically,
this is the
`ctags --fields=+S --output-format=json` output for the `main.py` file mapped above:

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

The repo map is built using this type of `ctags` data,
but formatted into the space
efficient hierarchical tree format shown earlier.
This is a format that GPT can easily understand
and which conveys the map data using a
minimal number of tokens.

## Example chat transcript

This
[chat transcript](https://aider.chat/examples/add-test.html)
shows GPT-4 creating a black box test case, **without being given
access to the source code of the function being tested or any of the
other code in the repo.** Instead, GPT is operating solely off
the repo map.

Using only the meta-data in the map, GPT is able to figure out how to call the method to be tested, as well as how to instantiate multiple class objects that are required to prepare for the test.

GPT makes one reasonable mistake writing the first version of the test, but is
able to quickly fix the issue after being shown the `pytest` error output.

## Future work

Just as "send the whole codebase to GPT with every request"
is not an efficient solution to this problem,
there are probably better approaches than
"send the whole repo map with every request".
Sending an appropriate subset of the repo map would help `aider` work
better with even larger repositories which have large maps.

Some possible approaches to reducing the amount of map data are:

  - Distill the global map, to prioritize important symbols and discard "internal" or otherwise less globally relevant identifiers. Possibly enlist `gpt-3.5-turbo` to perform this distillation in a flexible and language agnostic way.
  - Provide a mechanism for GPT to start with a distilled subset of the global map, and let it ask to see more detail about subtrees or keywords that it feels are relevant to the current coding task.
  - Attempt to analyze the natural language coding task given by the user and predict which subset of the repo map is relevant. Possibly by analysis of prior coding chats within the specific repo. Work on certain files or types of features may require certain somewhat predictable context from elsewhere in the repo. Vector and keyword search against the chat history, repo map or codebase may help here.

One key goal is to prefer solutions which are language agnostic or
which can be easily deployed against most popular code languages.
The `ctags` solution has this benefit, since it comes pre-built
with support for most popular languages.
I suspect that Language Server Protocol might be an even
better tool than `ctags` for this problem.
But it is more cumbersome to deploy for a broad
array of languages.
Users would need to stand up an LSP server for their
specific language(s) of interest.

## Try it out

To use this experimental repo map feature:

  - Install [aider](https://aider.chat/docs/install.html).
  - Install ctags.
  - Run `aider` inside your repo, and it should say "Repo-map: universal-ctags using 1024 tokens".
