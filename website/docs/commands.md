---
parent: Usage
nav_order: 50
description: Control aider with in-chat commands line /add, /model, etc.
---
# In-chat commands

Aider supports commands from within the chat, which all start with `/`.

<!--[[[cog
from aider.commands import get_help_md
cog.out(get_help_md())
]]]-->
- **/add** Add files to the chat so GPT can edit them or review them in detail
- **/clear** Clear the chat history
- **/commit** Commit edits to the repo made outside the chat (commit message optional)
- **/diff** Display the diff of the last aider commit
- **/drop** Remove files from the chat session to free up context space
- **/exit** Exit the application
- **/git** Run a git command
- **/help** Show help about all commands
- **/lint** Lint and fix provided files or in-chat files if none provided
- **/ls** List all known files and indicate which are included in the chat session
- **/model** Switch to a new LLM
- **/models** Search the list of available models
- **/quit** Exit the application
- **/run** Run a shell command and optionally add the output to the chat (alias: !)
- **/test** Run a shell command and add the output to the chat on non-zero exit code
- **/tokens** Report on the number of tokens used by the current chat context
- **/undo** Undo the last git commit if it was done by aider
- **/voice** Record and transcribe voice input
- **/web** Use headless selenium to scrape a webpage and add the content to the chat
<!--[[[end]]]-->

# Keybindings

The interactive prompt is built with [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) which provides a lot of Emacs and Vi-style keyboard. Some emacs bindings you may find useful are

- `Ctrl-A` : Move cursor to the start of the line.
- `Ctrl-B` : Move cursor back one character.
- `Ctrl-D` : Delete the character under the cursor.
- `Ctrl-E` : Move cursor to the end of the line.
- `Ctrl-F` : Move cursor forward one character.
- `Ctrl-K` : Delete from the cursor to the end of the line.
- `Ctrl-L` : Clear the screen.
- `Ctrl-N` : Move down to the next history entry.
- `Ctrl-P` : Move up to the previous history entry.
- `Ctrl-R` : Reverse search in command history.

Note: aider currently exits vi normal mode after a single command, (maybe something to do with the esc keybinding?).
Feel free to investigate and make a PR if you would like to see it fully supported.
