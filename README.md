# aider is GPT-4 powered coding in your terminal

`aider` is a command-line chat tool that allows you to write and edit
code with GPT-4.  You can ask GPT to help you start
a new project, or add features to your existing code.
`aider` is well suited for working with code in a git repo,
as it has features to easily
commit, diff and undo changes proposed by GPT. 

![aider screenshot](screenshot.gif)

## Example chat transcripts

Here are some example transcripts that show how you can chat with `aider` to write and edit code with GPT-4. 

* [**Hello World Flask App**](https://aider.chat/examples/hello-world-flask.html): Start from scratch and have GPT create a simple Flask app with various endpoints, such as adding two numbers and calculating the Fibonacci sequence.

* [**Javascript Game Modification**](https://aider.chat/examples/2048-game.html): Dive into an existing open-source repo, and get GPT's help to understand it and make modifications.

* [**Complex Multi-file Change with Debugging**](https://aider.chat/examples/complex-change.html): GPT makes a complex code change that is coordinated across multiple source files, and resolves bugs by reviewing error output and doc snippets.

* [**Create a Black Box Test Case**](https://aider.chat/examples/add-test.html): GPT creates a "black box" test case without access to the source of the method being tested, using only a
[high level map of the repository based on ctags](https://aider.chat/docs/ctags.html).

* [**Download, analyze and plot US Census data**](https://aider.chat/examples/census.html): GPT-4 downloads census data, suggests some hypotheses to test, tests one and then summarizes and plots a graph of the results.

You can find more chat transcripts on the [examples page](https://aider.chat/examples/).

## Features

* Chat with GPT-4 about your code by launching `aider` from the command line with set of source files to discuss and edit together.
* Request new features, changes, improvements, or bug fixes to your code. Ask for new test cases, updated documentation or code refactors.
* `aider` will apply the edits suggested by GPT-4 directly to your source files.
* `aider` will automatically commit each changeset to your local git repo with a descriptive commit message. These frequent, automatic commits provide a safety net. It's easy to undo `aider` changes or use standard git workflows to manage longer sequences of changes.
* `aider` can review multiple source files at once and make coordinated code changes across all of them in a single changeset/commit.
* `aider` can give GPT a
[map of your entire git repo](https://aider.chat/docs/ctags.html),
which helps it understand and modify large codebases.
* You can edit the files by hand using your editor while chatting with `aider`.
  * `aider` will notice if you edit the files outside the chat.
  * It will help you commit these out-of-band changes, if you'd like.
  * It will bring the updated file contents into the chat.
  * You can bounce back and forth between the `aider` chat and your editor, to fluidly collaborate.
* Live, colorized, human friendly output.
* Readline style chat input history, with autocompletion of code tokens found in the source files being discussed (via `prompt_toolkit` and `pygments` lexers)

## Installation

1. Install the package:
    * From GitHub: `pip install git+https://github.com/paul-gauthier/aider.git`
    * From your local copy of the repo in develop mode to pick up local edits immediately: `pip install -e .` 

2. Set up your OpenAI API key as an environment variable `OPENAI_API_KEY` or by including it in an `.aider.config.yml` file (see `aider --help`).

3. Optionally, install [universal ctags](https://github.com/universal-ctags/ctags). This is helpful if you plan to work with repositories with more than a handful of files.  This allows `aider --ctags` to build a [map of your entire git repo](https://aider.chat/docs/ctags.html) and share it with GPT to help it better understand and modify large codebases.

## Usage

Run the `aider` tool by executing the following command:

```
aider <file1> <file2> ...
```

Replace `<file1>`, `<file2>`, etc., with the paths to the source code files you want to work on. These files will be added to the chat session.

You can also just launch `aider` anywhere in a git repo without naming files on the command line.
It will discover all the files in the repo.
You can then add and remove individual files in the chat session with the `/add` and `/drop` chat commands described below.

You can also use additional command-line options, environment variables or configuration file
to set many options:

```
  -c CONFIG_FILE, --config CONFIG_FILE
                        Specify the config file (default: search for .aider.conf.yml in git root or home directory)
  --input-history-file INPUT_HISTORY_FILE
                        Specify the chat input history file (default: .aider.input.history) [env var: AIDER_INPUT_HISTORY_FILE]
  --chat-history-file CHAT_HISTORY_FILE
                        Specify the chat history file (default: .aider.chat.history.md) [env var: AIDER_CHAT_HISTORY_FILE]
  --model MODEL         Specify the model to use for the main chat (default: gpt-4) [env var: AIDER_MODEL]
  -3                    Use gpt-3.5-turbo model for the main chat (not advised)
  --pretty              Enable pretty, colorized output (default: True) [env var: AIDER_PRETTY]
  --no-pretty           Disable pretty, colorized output [env var: AIDER_NO_PRETTY]
  --apply FILE          Apply the changes from the given file instead of running the chat (debug) [env var: AIDER_APPLY]
  --auto-commits        Enable auto commit of changes (default: True) [env var: AIDER_AUTO_COMMITS]
  --no-auto-commits     Disable auto commit of changes [env var: AIDER_NO_AUTO_COMMITS]
  --dirty-commits       Enable dirty commit of changes [env var: AIDER_DIRTY_COMMITS]
  --no-dirty-commits    Disable dirty commit of changes [env var: AIDER_NO_DIRTY_COMMITS]
  --openai-api-key OPENAI_API_KEY
                        Specify the OpenAI API key [env var: OPENAI_API_KEY]
  --dry-run             Perform a dry run without applying changes (default: False) [env var: AIDER_DRY_RUN]
  --show-diffs          Show diffs when committing changes (default: False) [env var: AIDER_SHOW_DIFFS]
  --ctags [CTAGS]       Add ctags to the chat to help GPT understand the codebase (default: check for ctags executable) [env var: AIDER_CTAGS]
  --yes                 Always say yes to every confirmation [env var: AIDER_YES]
  -v, --verbose         Enable verbose output [env var: AIDER_VERBOSE]
```

## Chat commands

`aider` supports the following commands from within the chat:

* `/add <file>`: Add matching files to the chat session.
* `/drop <file>`: Remove matching files from the chat session.
* `/ls`: List all known files and those included in the chat session.
* `/commit [message]`: Commit outstanding changes to the repo. Use this to commit edits you made outside the chat, with your editor or git commands. aider will provide a commit message if you don't.
* `/undo`: Undo the last git commit if it was done by aider.
* `/diff`: Display the diff of the last aider commit.
* `/run <command>`: Run a shell command and optionally add the output to the chat.
* `/help`: Show help about all commands.

To use a command, simply type it in the chat input followed by any required arguments.

## Tips

* Large changes are best performed as a sequence of bite sized steps. Same as if you were undertaking them by yourself.
* Use Control-C to safely interrupt `aider` if it isn't providing a useful response. The partial response remains in the conversation, so you can refer to it when you reply with more information or direction.
* Use the `/run` command to run tests, linters, etc and show the output to GPT so it can fix any issues.
* Enter a multiline chat message by entering `{` alone on the first line. End the multiline message with `}` alone on the last line.
* If your code is throwing an error, paste the error message and stack trace into `aider` as a multiline `{}` message and let `aider` fix the bug.
* GPT-4 knows about a lot of standard tools and libraries, but may get some of the fine details wrong about APIs and function arguments. You can paste doc snippets into the chat with the  multiline `{}` syntax.
* `aider` will notice if you launch it on a git repo with uncommitted changes and offer to commit them before proceeding.
* `aider` can only see the content of the files you specify, but it also gets a list of all the files in the repo. It may ask to see additional files if it feels that's needed for your requests.

## Limitations

You probably need GPT-4 api access to use `aider`.
You can invoke it with `aider -3` to try using gpt-3.5-turbo, but it will almost certainly fail to function correctly.
GPT-3.5 is unable to consistently follow directions to generate concise code edits in a stable, parsable format.

You can only use `aider` to edit code that fits in the GPT context window.
For GPT-4 that is 8k tokens.
It helps to be selective about how many source files you discuss with `aider` at one time.
You might consider refactoring your code into more, smaller files (which is usually a good idea anyway).
You can use `aider` to help perform such refactorings, if you start before the files get too large.

If you have access to gpt-4-32k, I would be curious to hear how it works with aider.

