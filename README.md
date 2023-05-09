# Aider

Aider is a command-line tool that allows you to chat with GPT about your code.
It can make changes, improvements, and bug fixes to your code with the assistance of GPT.

## Features

* Chat with GPT about your code by specifying a set of source files to discuss
* Request changes, improvements, and bug fixes to your code
* Aider will apply the edits suggested by GPT.
* Aider will automatically commit each change to a git repo with a sensible commit message, providing safety, edit history and easy undo with normal git tools
* Live, colorized, human friendly output
* Can make coordinated changes across multiple source files
* Readline style chat input history, with autocompletion of tokens found in source files being discussed

## Installation

1. Clone the repository.
2. Install the required packages using `pip install -r requirements.txt`.
3. Set up your OpenAI API key as an environment variable `OPENAI_API_KEY`.

## Usage

Run the Aider tool by executing the following command:

```
aider <file1> <file2> ...
```

Replace `<file1>`, `<file2>`, etc., with the paths to the source code files you want to work on.

You can also use additional command-line options to customize the behavior of the tool. For more information, run `aider --help`. Many defaults can be set with `.env` or environment variables, see the help output.

## Limitations

Aider basically requires GPT-4 for the main chat functions.
You can invoke it with `aider -3` to try using gpt-3.5-turbo, but it will almost certainly fail to function correctly.
GPT-3.5 is unable to follow directions and generate code changes in a stable, parsable format.

Aider also can only edit code that can fit in the context window.
For GPT-4 that is 8k tokens.
If you have access to gpt-4-32k, I would be curious to hear you experiences using it with aider.

