# aider is GPT powered coding in your terminal

`aider` is a command-line chat tool that allows you to write and edit
code with gpt-4 or gpt-3.5-turbo.  You can ask GPT to help you start
a new project, or modify code in your existing git repo.
Aider makes it easy to git commit, diff & undo changes proposed by GPT without copy/pasting. 
It also has features that [help GPT-4 understand and modify larger codebases](https://aider.chat/docs/ctags.html).

![aider screencast](assets/screencast.svg)

- [Getting started](#getting-started)
- [Example chat transcripts](#example-chat-transcripts)
- [Features](#features)
- [GPT-4 vs GPT-3.5](#gpt-4-vs-gpt-35)
- [Installation](#installation)
- [Usage](#usage)
- [In-chat commands](#in-chat-commands)
- [Tips](#tips)
- [Limitations](#limitations)

## Getting started

```
$ pip install git+https://github.com/paul-gauthier/aider.git
$ export OPENAI_API_KEY=sk-...
$ aider myapp.py

Using git repo: .git
Added myapp.py to the chat.

myapp.py> change the fibonacci function from recursion to iteration
```

## Example chat transcripts

Here are some example transcripts that show how you can chat with `aider` to write and edit code with GPT-4. 

* [**Hello World Flask App**](https://aider.chat/examples/hello-world-flask.html): Start from scratch and have GPT create a simple Flask app with various endpoints, such as adding two numbers and calculating the Fibonacci sequence.

* [**Javascript Game Modification**](https://aider.chat/examples/2048-game.html): Dive into an existing open-source repo, and get GPT's help to understand it and make modifications.

* [**Complex Multi-file Change with Debugging**](https://aider.chat/examples/complex-change.html): GPT makes a complex code change that is coordinated across multiple source files, and resolves bugs by reviewing error output and doc snippets.

* [**Create a Black Box Test Case**](https://aider.chat/examples/add-test.html): GPT creates a "black box" test case without access to the source of the method being tested, using only a
[high level map of the repository based on ctags](https://aider.chat/docs/ctags.html).

You can find more chat transcripts on the [examples page](https://aider.chat/examples/).

## Features

* Chat with GPT about your code by launching `aider` from the command line with set of source files to discuss and edit together. Aider lets GPT see and edit the content of those files.
* Request new features, changes, improvements, or bug fixes to your code. Ask for new test cases, updated documentation or code refactors.
* Aider will apply the edits suggested by GPT directly to your source files.
* Aider will automatically commit each changeset to your local git repo with a descriptive commit message. These frequent, automatic commits provide a safety net. It's easy to undo changes or use standard git workflows to manage longer sequences of changes.
* Aider can review multiple source files at once so GPT can make coordinated code changes across all of them in a single changeset/commit.
* Aider can give *GPT-4* a
[map of your entire git repo](https://aider.chat/docs/ctags.html),
which helps it understand and modify large codebases.
* You can also edit files by hand using your editor while chatting with `aider`. Aider will notice these out-of-band edits and ask if you'd like to commit them. This lets you bounce back and forth between the `aider` chat and your editor, to collaboratively code with GPT.

## GPT-4 vs GPT-3.5

You need an
[OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key)
to use aider.
Aider supports the `gpt-4` model and has new, experimental support for `gpt-3.5-turbo`.

You will get better results with GPT-4, for a few reasons:

  - GPT-3.5 isn't able to reliably follow instructions to output "diff style" edits to files. So to make an edit, it has to return a whole new copy of the code that includes any changes. This uses up a lot of the already small GPT-3.5 context window.
  - GPT-4 has a much larger context window and is able to reliably generate "diff style" edits to files. This allows you to edit much larger files when using aider with GPT-4.
  - GPT-4's larger context window also allows aider to include a [concise map of your repository](https://aider.chat/docs/ctags.html) with each of your change requests. This helps GPT-4 successfully make bigger, more complex changes inside larger pre-existing codebases.

## Installation

1. Install the package:
    * From GitHub: `pip install git+https://github.com/paul-gauthier/aider.git`
    * From your local copy of the repo in develop mode to pick up local edits immediately: `pip install -e .` 

2. Set up your OpenAI API key as an environment variable `OPENAI_API_KEY` or by including `openai-api-key: sk-...` in an `.aider.config.yml` file (see `aider --help`).

3. Optionally, install [universal ctags](https://github.com/universal-ctags/ctags). This is helpful if you plan to use aider and GPT-4 with repositories that have more than a handful of files.  This allows `aider` to build a [map of your entire git repo](https://aider.chat/docs/ctags.html) and share it with GPT to help it better understand and modify large codebases.

## Usage

Run the `aider` tool by executing the following command:

```
aider <file1> <file2> ...
```

Replace `<file1>`, `<file2>`, etc., with the paths to the source code files you want to work on. These files will be added to the chat session.

You can also just launch `aider` anywhere in a git repo without naming
files on the command line.  It will discover all the files in the
repo.  You can then add and remove individual files in the chat
session with the `/add` and `/drop` chat commands described below.
If you or GPT mention one of the repo's filenames in the conversation,
`aider` will ask if you'd like to add it to the chat.

You can also use additional command-line options, environment variables or configuration file
to set many options. See `aider --help` for details.

## In-chat commands

`aider` supports commands from within the chat, which all start with `/`. Here are some of the most useful in-chat commands:

* `/add <file>`: Add matching files to the chat session.
* `/drop <file>`: Remove matching files from the chat session.
* `/undo`: Undo the last git commit if it was done by aider.
* `/diff`: Display the diff of the last aider commit.
* `/run <command>`: Run a shell command and optionally add the output to the chat.
* `/help`: Show help about all commands.

## Tips

* Large changes are best performed as a sequence of thoughtful bite sized steps, where you plan out the approach and overall design. Walk GPT through changes like you might with a junior dev. Ask for a refactor to prepare, then ask for the actual change. Spend the time to ask for code quality/structure improvements.
* Use Control-C to safely interrupt `aider` if it isn't providing a useful response. The partial response remains in the conversation, so you can refer to it when you reply to GPT with more information or direction.
* Use the `/run` command to run tests, linters, etc and show the output to GPT so it can fix any issues.
* Enter a multiline chat message by entering `{` alone on the first line. End the multiline message with `}` alone on the last line.
* If your code is throwing an error, share the error output with GPT using `/run` or by pasting it into the chat. Let GPT figure out and fix the bug.
* GPT knows about a lot of standard tools and libraries, but may get some of the fine details wrong about APIs and function arguments. You can paste doc snippets into the chat to resolve these issues.
* `aider` will notice if you launch it on a git repo with uncommitted changes and offer to commit them before proceeding.
* GPT can only see the content of the files you specifically "add to the chat". Aider also sends GPT-4 a [map of your entire git repo](https://aider.chat/docs/ctags.html). So GPT may ask to see additional files if it feels that's needed for your requests.
* I also shared some more [GPT coding tips on Hacker News](https://news.ycombinator.com/item?id=36211879).

## Limitations

You can only use `aider` to edit code that fits in the GPT context window.
For GPT-4 that is 8k tokens, and for GPT-3.5 that is 4k tokens.
Aider lets you manage the context window by
being selective about how many source files you discuss with `aider` at one time.
You might consider refactoring your code into more, smaller files (which is usually a good idea anyway).
You can use `aider` to help perform such refactorings, if you start before the files get too large.

If you have access to gpt-4-32k, I would be curious to hear how it works with aider.
