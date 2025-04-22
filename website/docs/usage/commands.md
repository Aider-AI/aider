# Commands

Aider has a number of commands that can be used to control its behavior. Commands start with a `/` or `!`.

|Command|Description|
|:------|:----------|
| `/add`          | Add files to the chat so aider can edit them or review them in detail. |
| `/ask`          | Ask questions about the code base without editing any files. If no prompt provided, switches to ask mode. |
| `/architect`    | *Deprecated* – now a thin wrapper around `/macro examples/architect_macro.py`. |
| `/chat-mode`    | Switch to a new chat mode. |
| `/clear`        | Clear the chat history. |
| `/code`         | Ask for changes to your code. If no prompt provided, switches to code mode. |
| `/commit`       | Commit edits to the repo made outside the chat (commit message optional). |
| `/context`      | Enter context mode to see surrounding code context. If no prompt provided, switches to context mode. |
| `/copy`         | Copy the last assistant message to the clipboard. |
| `/copy-context` | Copy the current chat context as markdown, suitable to paste into a web UI. |
| `/diff`         | Display the diff of changes since the last message. |
| `/drop`         | Remove files from the chat session to free up context space. |
| `/edit`         | Alias for /editor: Open an editor to write a prompt. |
| `/editor`       | Open an editor to write a prompt. |
| `/exit`         | Exit the application. |
| `/help`         | Ask questions about aider. |
| `/lint`         | Lint and fix in-chat files or all dirty files if none in chat. |
| `/load`         | Load and execute commands from a file. |
| `/ls`           | List all known files and indicate which are included in the chat session. |
+| `/macro`        | Run a Python macro file (`/macro script.py k=v …`). |
| `/map`          | Print out the current repository map. |
| `/map-refresh`  | Force a refresh of the repository map. |
| `/model`        | Switch the Main Model to a new LLM. |
| `/models`       | Search the list of available models. |
| `/multiline-mode`| Toggle multiline mode (swaps behavior of Enter and Meta+Enter). |
| `/paste`        | Paste image/text from the clipboard into the chat. Optionally provide a name for the image. |
| `/quit`         | Exit the application. |
| `/read-only`    | Add files to the chat that are for reference only, or turn added files to read-only. |
| `/reasoning-effort`| Set the reasoning effort level (values: number or low/medium/high depending on model). |
| `/report`       | Report a problem by opening a GitHub Issue. |
| `/reset`        | Drop all files and clear the chat history. |
| `/run`          | Execute a shell command. |
| `/save`         | Save commands to a file that can reconstruct the current chat session's files. |
| `/settings`     | Print out the current settings. |
| `/test`         | Run a shell command and add the output to the chat on non-zero exit code. |
| `/think-tokens` | Set the thinking token budget (supports formats like 8096, 8k, 10.5k, 0.5M). |
| `/undo`         | Undo the last git commit if it was done by aider. |
| `/voice`        | Record and transcribe voice input. |

You can also use `!command` as an alias for `/run command`.
