# aider is GPT powered coding in your terminal

`aider` is a command-line chat tool that allows you to write and edit
code with OpenAI's GPT models.  You can ask GPT to help you start
a new project, or modify code in your existing git repo.
Aider makes it easy to git commit, diff & undo changes proposed by GPT without copy/pasting. 
It also has features that [help GPT-4 understand and modify larger codebases](https://aider.chat/docs/ctags.html).

![aider screencast](assets/screencast.svg)

- [Getting started](#getting-started)
- [Example chat transcripts](#example-chat-transcripts)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [In-chat commands](#in-chat-commands)
- [Tips](#tips)
- [GPT-4 vs GPT-3.5](#gpt-4-vs-gpt-35)

## Getting started

```
$ pip install aider-chat
$ export OPENAI_API_KEY=your-key-goes-here
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
* You can use aider with multiple source files at once, so GPT can make coordinated code changes across all of them in a single changeset/commit.
* Aider can [give *GPT-4* a map of your entire git repo](https://aider.chat/docs/ctags.html), which helps it understand and modify large codebases.
* You can also edit files by hand using your editor while chatting with aider. Aider will notice these out-of-band edits and ask if you'd like to commit them. This lets you bounce back and forth between the aider chat and your editor, to collaboratively code with GPT.


## Installation

1. Install the package:
  * PyPI: `pip install aider-chat`
  * GitHub: `pip install git+https://github.com/paul-gauthier/aider.git`
  * Local clone: `pip install -e .` 

2. Set up your OpenAI API key:
  * As an environment variable: `export OPENAI_API_KEY=sk-...`
  * Or, by including `openai-api-key: sk-...` in an `.aider.config.yml` file

3. Optionally, install [universal ctags](https://github.com/universal-ctags/ctags). This is helpful if you plan to use aider and GPT-4 with repositories that have more than a handful of files.  This allows aider to build a [map of your entire git repo](https://aider.chat/docs/ctags.html) and share it with GPT to help it better understand and modify large codebases.

## Usage

Run the `aider` tool by executing the following command:

```
aider <file1> <file2> ...
```

Replace `<file1>`, `<file2>`, etc., with the paths to the source code files you want to work on.
These files will be "added to the chat session", so that GPT can see their contents and edit them according to your instructions.

You can also just launch `aider` anywhere in a git repo without naming
files on the command line.  It will discover all the files in the
repo.  You can then add and remove individual files in the chat
session with the `/add` and `/drop` chat commands described below.
If you or GPT mention one of the repo's filenames in the conversation,
aider will ask if you'd like to add it to the chat.

Aider will work best if you think about which files need to be edited to make your change and add them to the chat.
Aider has some ability to help GPT figure out which files to edit all by itself, but the most effective approach is to explicitly add the needed files to the chat yourself.

Aider also has many
additional command-line options, environment variables or configuration file
to set many options. See `aider --help` for details.

## In-chat commands

Aider supports commands from within the chat, which all start with `/`. Here are some of the most useful in-chat commands:

* `/add <file>`: Add matching files to the chat session.
* `/drop <file>`: Remove matching files from the chat session.
* `/undo`: Undo the last git commit if it was done by aider.
* `/diff`: Display the diff of the last aider commit.
* `/run <command>`: Run a shell command and optionally add the output to the chat.
* `/help`: Show help about all commands.


## Tips

* Think about which files need to be edited to make your change and add them to the chat.
Aider has some ability to help GPT figure out which files to edit all by itself, but the most effective approach is to explicitly add the needed files to the chat yourself. 
* Large changes are best performed as a sequence of thoughtful bite sized steps, where you plan out the approach and overall design. Walk GPT through changes like you might with a junior dev. Ask for a refactor to prepare, then ask for the actual change. Spend the time to ask for code quality/structure improvements.
* Use Control-C to safely interrupt GPT if it isn't providing a useful response. The partial response remains in the conversation, so you can refer to it when you reply to GPT with more information or direction.
* Use the `/run` command to run tests, linters, etc and show the output to GPT so it can fix any issues.
* Enter a multiline chat message by entering `{` alone on the first line. End the multiline message with `}` alone on the last line.
* If your code is throwing an error, share the error output with GPT using `/run` or by pasting it into the chat. Let GPT figure out and fix the bug.
* GPT knows about a lot of standard tools and libraries, but may get some of the fine details wrong about APIs and function arguments. You can paste doc snippets into the chat to resolve these issues.
* Aider will notice if you launch it on a git repo with uncommitted changes and offer to commit them before proceeding.
* GPT can only see the content of the files you specifically "add to the chat". Aider also sends GPT-4 a [map of your entire git repo](https://aider.chat/docs/ctags.html). So GPT may ask to see additional files if it feels that's needed for your requests.
* I also shared some general [GPT coding tips on Hacker News](https://news.ycombinator.com/item?id=36211879).

## GPT-4 vs GPT-3.5

Aider supports all of OpenAI's chat models, including
the the brand new `gpt-3.5-turbo-16k` model. 

You will probably get the best results with one of the GPT-4 models,
because of their large context windows,
adherance to system prompt instructions and
greater competance at coding tasks.
The GPT-4 models are able to structure code edits as simple "diffs"
and use a
[repository map](https://aider.chat/docs/ctags.html)
to improve their ability to make changes in larger codebases.

The GPT-3.5 models are supported more experimentally
and are limited to editing somewhat smaller codebases.
They are less able to follow instructions and
aren't able to return code edits in a compact "diff" format.
So aider has
to ask GPT-3.5 to return a new copy of the "whole file" with edits included.
This rapidly uses up tokens and can hit the limits of the context window.

Aider disables the
[repository map feature](https://aider.chat/docs/ctags.html)
when used with GPT-3.5 models.
The `gpt-3.5-turbo` context window is too small to include a repo map.
Evaluation is still needed to determine if `gpt-3.5-turbo-16k` can make use of a repo map.

In practice, this means you can use aider to edit a set of source files
that total up to the sizes below.
You can (and should) add just the specific set of files to the chat
that are relevant to the change you are requesting.
This minimizes your use of the context window, as well as costs.

| Model             | Context<br>Size | Edit<br>Format | Max<br>File Size | Max<br>File Size | Repo<br>Map? |
| ----------------- | -- | --     | -----| -- | -- |
| gpt-3.5-turbo     |  4k tokens | whole file | 2k tokens | ~8k bytes | no |
| gpt-3.5-turbo-16k | 16k tokens | whole file | 8k tokens | ~32k bytes | no |
| gpt-4             |  8k tokens | diffs | 8k tokens | ~32k bytes | yes | 
| gpt-4-32k         | 32k tokens | diffs | 32k tokens  | ~128k bytes | yes |

## Kind words from users

* "Aider ... has easily quadrupled my coding productivity." -- [SOLAR_FIELDS](https://news.ycombinator.com/item?id=36212100)
* "What an amazing tool. It's incredible." -- [valyagolev](https://github.com/paul-gauthier/aider/issues/6#issue-1722897858)
* "It was WAY faster than I would be getting off the ground and making the first few working versions." -- [Daniel Feldman](https://twitter.com/d_feldman/status/1662295077387923456)

