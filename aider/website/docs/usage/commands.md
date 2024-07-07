---
parent: Usage
nav_order: 50
description: Control aider with in-chat commands like /add, /model, etc.
---
# In-chat commands

Aider supports commands from within the chat, which all start with `/`.

<!--[[[cog
from aider.commands import get_help_md
cog.out(get_help_md())
]]]-->

|Command|Description|
|:------|:----------|
| **/add** | Add files to the chat so GPT can edit them or review them in detail |
| **/clear** | Clear the chat history |
| **/commit** | Commit edits to the repo made outside the chat (commit message optional) |
| **/diff** | Display the diff of the last aider commit |
| **/drop** | Remove files from the chat session to free up context space |
| **/exit** | Exit the application |
| **/git** | Run a git command |
| **/help** | Ask questions about aider |
| **/lint** | Lint and fix provided files or in-chat files if none provided |
| **/ls** | List all known files and indicate which are included in the chat session |
| **/model** | Switch to a new LLM |
| **/models** | Search the list of available models |
| **/quit** | Exit the application |
| **/run** | Run a shell command and optionally add the output to the chat (alias: !) |
| **/test** | Run a shell command and add the output to the chat on non-zero exit code |
| **/tokens** | Report on the number of tokens used by the current chat context |
| **/undo** | Undo the last git commit if it was done by aider |
| **/voice** | Record and transcribe voice input |
| **/web** | Use headless selenium to scrape a webpage and add the content to the chat |

<!--[[[end]]]-->

{: .tip }
You can easily re-send commands or messages.
Use the up arrow ⬆ to scroll back
or CONTROL-R to search your message history.

# Entering multi-line chat messages

{% include multi-line.md %}

# Keybindings

The interactive prompt is built with [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) which provides emacs and vi keybindings. 

## Emacs

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


## Vi

To use vi/vim keybindings, run aider with the `--vim` switch.

- `Esc` : Switch to command mode.
- `i` : Switch to insert mode.
- `a` : Move cursor one character to the right and switch to insert mode.
- `A` : Move cursor to the end of the line and switch to insert mode.
- `I` : Move cursor to the beginning of the line and switch to insert mode.
- `h` : Move cursor one character to the left.
- `j` : Move cursor down one line.
- `k` : Move cursor up one line.
- `l` : Move cursor one character to the right.
- `w` : Move cursor forward one word.
- `b` : Move cursor backward one word.
- `0` : Move cursor to the beginning of the line.
- `$` : Move cursor to the end of the line.
- `x` : Delete the character under the cursor.
- `dd` : Delete the current line.
- `u` : Undo the last change.
- `Ctrl-R` : Redo the last undone change.


