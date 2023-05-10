# Aider

Aider is a command-line tool that allows you to chat with GPT-4 about your code.
It can make changes, improvements, and bug fixes to the code in your local git repo.
Each change is automatically committed to git with a sensible commit message.

[![asciicast](https://asciinema.org/a/Ol6alHMmm4ZrVcOfXkMveS7eQ.svg)](https://asciinema.org/a/Ol6alHMmm4ZrVcOfXkMveS7eQ)

## Features

* Chat with GPT-4 about your code by launching aider with set of source files to discuss and edit together.
* Request changes, improvements, and bug fixes to your code.
* Aider will apply the edits suggested by GPT-4.
* Aider will automatically commit each changeset to git with a sensible commit message. These frequent, automatic commits provide a safety net. It's easy to use standard git workflows to either adopt or undo/abandon a series of changes.
* Aider can review multiple source files at once and make coordinated code changes across all of them in a single changeset/commit.
* You can also edit the files in your editor while chatting with aider.
  * Aider will notice if you edit the files outside the chat.
  * It will help you commit these out-of-band changes, if you'd like.
  * It will import the new file contents into the chat.
  * You can bounce back and forth between the aider chat and your editor, to fluidly collaborate.
* Live, colorized, human friendly output.
* Readline style chat input history, with autocompletion of tokens found in the source files being discussed (via `prompt_toolkit`)

## Installation

1. Install the package: `pip install git+https://github.com/paul-gauthier/aider.git`
2. Set up your OpenAI API key as an environment variable `OPENAI_API_KEY` or by including it in a `.env` file.

## Usage

Run the Aider tool by executing the following command:

```
aider <file1> <file2> ...
```

Replace `<file1>`, `<file2>`, etc., with the paths to the source code files you want to work on.

You can also use additional command-line options to customize the behavior of the tool. For more information, run `aider --help`. Many defaults can be set with `.env` or environment variables, see the help output.

## Commands

Aider supports the following commands from within the chat:

* `/add <file>`: Add matching files to the chat.
* `/drop <file>`: Remove matching files from the chat.
* `/ls`: List files and show their chat status.
* `/commit [message]`: Commit outstanding changes to the chat files. Aider will provide a commit message if you don't.
* `/undo`: Undo the last git commit if it was done by aider.
* `/diff`: Display the diff of the last aider commit.

To use a command, simply type it in the chat input followed by any required arguments.

## Tips

* Large changes are best performed as a sequence of bite sized steps. Same as if you were undertaking them by yourself.
* Use Control-C to safely interrupt aider if it isn't providing a useful response. The partial response remains in the conversation, so you can refer to it when you reply with more information or direction.
* Enter a multiline chat message by entering `{` alone on the first line. End the multiline message with `}` alone on the last line.
* If your code is throwing an error, paste the error message and stack trace into aider as a multiline `{}` message and let aider fix the bug.
* GPT-4 knows about a lot of standard tools and libraries, but may get some of the fine details wrong about APIs and function arguments. You can paste doc snippets into the chat with the  multiline `{}` syntax.
* Aider will notice if you launch it on files with uncommitted changes and offer to commit them before proceeding.
* Aider can only see the content of the files you specify, but it also gets a list of all the files in the repo. It may ask to see additional files if it feels that's needed for your requests. Relaunch with the additional files on the command line. Use the up-arrow to re-issue your request from the chat input history.

## Limitations

Aider basically requires GPT-4.
You can invoke it with `aider -3` to try using gpt-3.5-turbo, but it will almost certainly fail to function correctly.
GPT-3.5 is unable to consistently follow directions to generate concise code edits in a stable, parsable format.

Aider can only edit code that fits in the GPT context window.
For GPT-4 that is 8k tokens.
It helps to be selective about which of your source files you discuss with aider at the same time.
It can also help to refactor your code into more, smaller files.
Aider can help perform such refactorings, if you start before the files get too large.

If you have access to gpt-4-32k, I would be curious to hear how it works with aider.
