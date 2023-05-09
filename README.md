# Aider

Aider is a command-line tool that allows you to chat with GPT about your code.
It can make changes, improvements, and bug fixes to your code with the assistance of GPT.

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

You can also use additional command-line options to customize the behavior of the tool. For more information, run:

```
python -m aider.main --help
```
