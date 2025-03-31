---
parent: Usage
nav_order: 50
description: Control aider with in-chat commands like /add, /model, etc.
---

# In-chat commands
{: .no_toc }

- TOC
{:toc}

## Slash commands

Aider supports commands from within the chat, which all start with `/`.

<!--[[[cog
from aider.commands import get_help_md
cog.out(get_help_md())
]]]-->

|Command|Description|
|:------|:----------|
| **/add** | Add files to the chat so aider can edit them or review them in detail |
| **/architect** | Enter architect/editor mode using 2 different models. If no prompt provided, switches to architect/editor mode. |
| **/ask** | Ask questions about the code base without editing any files. If no prompt provided, switches to ask mode. |
| **/chat-mode** | Switch to a new chat mode |
| **/clear** | Clear the chat history |
| **/code** | Ask for changes to your code. If no prompt provided, switches to code mode. |
| **/commit** | Commit edits to the repo made outside the chat (commit message optional) |
| **/context** | Enter context mode to see surrounding code context. If no prompt provided, switches to context mode. |
| **/copy** | Copy the last assistant message to the clipboard |
| **/copy-context** | Copy the current chat context as markdown, suitable to paste into a web UI |
| **/diff** | Display the diff of changes since the last message |
| **/drop** | Remove files from the chat session to free up context space |
| **/edit** | Alias for /editor: Open an editor to write a prompt |
| **/editor** | Open an editor to write a prompt |
| **/editor-model** | Switch the Editor Model to a new LLM |
| **/exit** | Exit the application |
| **/git** | Run a git command (output excluded from chat) |
| **/help** | Ask questions about aider |
| **/lint** | Lint and fix in-chat files or all dirty files if none in chat |
| **/load** | Load and execute commands from a file |
| **/ls** | List all known files and indicate which are included in the chat session |
| **/map** | Print out the current repository map |
| **/map-refresh** | Force a refresh of the repository map |
| **/model** | Switch the Main Model to a new LLM |
| **/models** | Search the list of available models |
| **/multiline-mode** | Toggle multiline mode (swaps behavior of Enter and Meta+Enter) |
| **/paste** | Paste image/text from the clipboard into the chat.        Optionally provide a name for the image. |
| **/quit** | Exit the application |
| **/read-only** | Add files to the chat that are for reference only, or turn added files to read-only |
| **/reasoning-effort** | Set the reasoning effort level (values: number or low/medium/high depending on model) |
| **/report** | Report a problem by opening a GitHub Issue |
| **/reset** | Drop all files and clear the chat history |
| **/run** | Run a shell command and optionally add the output to the chat (alias: !) |
| **/save** | Save commands to a file that can reconstruct the current chat session's files |
| **/settings** | Print out the current settings |
| **/test** | Run a shell command and add the output to the chat on non-zero exit code |
| **/think-tokens** | Set the thinking token budget (supports formats like 8096, 8k, 10.5k, 0.5M) |
| **/tokens** | Report on the number of tokens used by the current chat context |
| **/undo** | Undo the last git commit if it was done by aider |
| **/voice** | Record and transcribe voice input |
| **/weak-model** | Switch the Weak Model to a new LLM |
| **/web** | Scrape a webpage, convert to markdown and send in a message |

<!--[[[end]]]-->

{: .tip }
You can easily re-send commands or messages.
Use the up arrow ⬆ to scroll back
or CONTROL-R to search your message history.

## Entering multi-line chat messages

{% include multi-line.md %}

## Interrupting with CONTROL-C

It's always safe to use Control-C to interrupt aider if it isn't providing a useful response. The partial response remains in the conversation, so you can refer to it when you reply to the LLM with more information or direction.

## Keybindings

The interactive prompt is built with [prompt-toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) which provides emacs and vi keybindings. 

### Emacs

- `Up Arrow` : Move up one line in the current message.
- `Down Arrow` : Move down one line in the current message.
- `Ctrl-Up` : Scroll back through previously sent messages.
- `Ctrl-Down` : Scroll forward through previously sent messages.
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
- `Ctrl-X Ctrl-E` : Open the current input in an external editor
- `Ctrl-Y` : Paste (yank) text that was previously cut.


### Vi

To use vi/vim keybindings, run aider with the `--vim` switch.

- `Up Arrow` : Move up one line in the current message.
- `Down Arrow` : Move down one line in the current message.
- `Ctrl-Up` : Scroll back through previously sent messages.
- `Ctrl-Down` : Scroll forward through previously sent messages.
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


