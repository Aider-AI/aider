---
parent: Example chat transcripts
---
# Automatically update docs with aider

In this chat transcript, the user asks to automatically update the Usage docs based on the latest version of the main() function in the code.

<div class="chat-transcript" markdown="1">

> $ aider ./README.md aider/main.py  
> Added README.md to the chat  
> Added aider/main.py to the chat  

#### the cmd line args in main() have been updated. update the readme to accurately describe them.  

```markdown
README.md
<<<<<<< ORIGINAL
- `--history-file HISTORY_FILE`: Specify the chat input history file (default: .aider.history). Override the default with the environment variable `AIDER_HISTORY_FILE`.
- `--model MODEL`: Specify the model to use for the main chat (default: gpt-4). Override the default with the environment variable `AIDER_MODEL`.
- `-3`: Use gpt-3.5-turbo model for the main chat (basically won't work). No environment variable override.
- `--no-pretty`: Disable pretty, colorized output. Override the default with the environment variable `AIDER_PRETTY` (default: 1 for enabled, 0 for disabled).
- `--show-diffs`: Show diffs when committing changes (default: False). Override the default with the environment variable `AIDER_SHOW_DIFFS` (default: 0 for False, 1 for True).
- `--no-auto-commits`: Disable auto commit of changes. Override the default with the environment variable `AIDER_AUTO_COMMITS` (default: 1 for enabled, 0 for disabled).
=======
- `--input-history-file INPUT_HISTORY_FILE`: Specify the chat input history file (default: .aider.input.history). Override the default with the environment variable `AIDER_INPUT_HISTORY_FILE`.
- `--chat-history-file CHAT_HISTORY_FILE`: Specify the chat history file (default: .aider.chat.history.md). Override the default with the environment variable `AIDER_CHAT_HISTORY_FILE`.
- `--model MODEL`: Specify the model to use for the main chat (default: gpt-4). Override the default with the environment variable `AIDER_MODEL`.
- `-3`: Use gpt-3.5-turbo model for the main chat (basically won't work). No environment variable override.
- `--no-pretty`: Disable pretty, colorized output. Override the default with the environment variable `AIDER_PRETTY` (default: 1 for enabled, 0 for disabled).
- `--apply FILE`: Apply the changes from the given file instead of running the chat (debug).
- `--no-auto-commits`: Disable auto commit of changes. Override the default with the environment variable `AIDER_AUTO_COMMITS` (default: 1 for enabled, 0 for disabled).
- `--show-diffs`: Show diffs when committing changes (default: False). Override the default with the environment variable `AIDER_SHOW_DIFFS` (default: 0 for False, 1 for True).
- `--yes`: Always say yes to every confirmation (default: False).
>>>>>>> UPDATED
```

> Applied edit to README.md  
> Commit 024f45e aider: Updated command line arguments in main() and updated README.md to accurately describe them.  

</div>
