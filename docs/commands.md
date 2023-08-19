# Commands

- `/help`: Show help about all commands
- `/exit`: Exit the application

## context management
- `/add <file>`: Add matching files to the chat session using glob patterns
- `/drop <file>`: Remove matching files from the chat session
- `/clear`: Clear the chat history
- `/ls`: List all known files and those included in the chat session
- `/tokens`: Report on the number of tokens used by the current chat context

## git
- `/undo`: Undo the last git commit if it was done by aider
- `/diff`: Display the diff of the last aider commit
- `/commit <message>`: Commit edits to the repo made outside the chat (commit message optional)
- `/git <command>`: Run a git command

## other
- `/run <command>`: Run a shell command and optionally add the output to the chat
- `/voice`: Speak to aider to [request code changes with your voice](https://aider.chat/docs/voice.html).

# Prompt Toolkit defaults

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

Note: aider currently exits vi normal mode after a single command, (maybe something to do with the esc keybinding?). Feel free to investigate and make a PR if you would like to see it fully supported.

Prompt toolkit also does not provide clear documentation on the bindings they support - maybe you can take aider and help them out with that and we can then link to the authoritative docs.
