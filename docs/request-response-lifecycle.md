# Aider's Request/Response Lifecycle

This document breaks down the process that occurs from the moment a user enters a prompt in Aider to when the AI's response is processed and code changes are applied. The core of this logic resides in `aider/coders/base_coder.py`.

## High-Level Overview

The lifecycle can be visualized as a pipeline that gathers context, sends it to a Large Language Model (LLM), processes the response, and then acts upon it.

```text
+---------------------+
|     User Prompt     |
| "add a new feature" |
+---------------------+
         |
         v
+-------------------------------------------------+
| Coder.run_one("add a new feature")              |
| - Pre-process for commands, URLs, etc.          |
+-------------------------------------------------+
         |
         v
+-------------------------------------------------+
| Message Assembly (format_messages)              |
|                                                 |
|  +-------------------------------------------+  |
|  | System Prompt (from *prompts.py)          |  |
|  | + Platform Info (OS, shell...)            |  |
|  +-------------------------------------------+  |
|  +-------------------------------------------+  |
|  | Examples (for few-shot prompting)         |  |
|  +-------------------------------------------+  |
|  +-------------------------------------------+  |
|  | Chat History (summarized)                 |  |
|  +-------------------------------------------+  |
|  +-------------------------------------------+  |
|  | Repo Map / Files Context                  |  |
|  | (Contents of file1.py, file2.py...)       |  |
|  +-------------------------------------------+  |
|  +-------------------------------------------+  |
|  | Current User Prompt                       |  |
|  +-------------------------------------------+  |
|                                                 |
+-------------------------------------------------+
         |
         v
+-------------------------------------------------+
| send_message() -> LLM API Call                  |
+-------------------------------------------------+
         |
         v
+-------------------------------------------------+
| LLM Response (Streaming)                        |
| "Thinking..." -> "Explanation..." -> Code Edits |
+-------------------------------------------------+
         |
         v
+-------------------------------------------------+
| Post-processing & Actions                       |
| - Parse & apply edits (apply_updates)           |
| - Run shell commands                            |
| - Auto-lint, test, and commit                   |
+-------------------------------------------------+
         |
         v
+-------------------------------------------------+
| Display result & wait for next user prompt      |
+-------------------------------------------------+

```

## Step-by-Step Breakdown

### 1. User Input & Pre-processing

- **Input:** The `Coder.run()` method in `base_coder.py` captures user input via `io.get_input()`.
- **Pre-processing:** The `preproc_user_input` method is called.
    - It checks if the input is a command (e.g., `/add`, `/drop`). If so, it's executed, and the cycle ends for that input.
    - It scans the input for URLs (`check_for_urls`) and file paths (`check_for_file_mentions`). If found, it may prompt the user to add them to the chat context.

### 2. Prompt Assembly (The Core)

This is the most critical phase, managed by `format_messages()` which uses `format_chat_chunks()`. The goal is to build a comprehensive context for the LLM. The `ChatChunks` class from `aider/coders/chat_chunks.py` organizes this context into distinct sections, which are then concatenated.

1.  **System Prompt:** The `fmt_system_prompt` method constructs the main instruction set. It pulls the base template from a prompts file like `aider/coders/editblock_prompts.py` and injects:
    *   Instructions for the specific edit format (e.g., `SEARCH/REPLACE` block rules).
    *   Platform information (`get_platform_info`): OS, shell, programming languages, and configured lint/test commands.
    *   Instructions on suggesting shell commands, sourced from `aider/coders/shell.py`.

2.  **Examples:** Few-shot examples are included from the prompts file to show the LLM the desired output format.

3.  **Chat History (`done_messages`):** A summarized history of the conversation is added to maintain context from previous turns.

4.  **Repository Context:**
    *   `get_repo_messages()`: If the repo-map feature is enabled, a summarized map of the entire repository is included.
    *   `get_readonly_files_messages()`: Contents of any files added as "read-only" are added as reference material.
    *   `get_chat_files_messages()`: The full contents of all files actively "in the chat" for editing are included.

5.  **Current User Prompt (`cur_messages`):** Finally, the user's most recent message is appended.

### 3. Sending to the LLM

- The assembled list of messages is passed to `send_message()`.
- A token count check (`check_tokens`) is performed to warn the user if the context size is approaching the model's limit.
- The payload is sent to the configured LLM via `litellm`. Aider primarily uses streaming responses.

### 4. Receiving and Processing the Response

- **Streaming:** The `show_send_output_stream` method processes the response in chunks.
    - It displays the output to the user in real-time. The "thinking" section is streamed first, followed by the explanation and code blocks.
    - The full response is gradually assembled into `self.partial_response_content`.
- **Cleanup:** Once the stream ends, `remove_reasoning_content` is called to strip the "thinking" section from the final assistant message, leaving only the actionable explanation and code.

### 5. Applying Changes and Post-Actions

- The response is parsed by methods like `get_edits()`.
- `apply_updates()` orchestrates the file modifications.
    - It first performs a dry run to validate the edits.
    - `prepare_to_edit()` checks if Aider is allowed to edit the targeted files, creating new files or asking for user permission if necessary.
    - `apply_edits()` writes the changes to the filesystem.
- If the LLM suggested shell commands, `run_shell_commands()` will prompt the user to execute them.

### 6. Auto-Actions and Looping

- If enabled, Aider performs several automated follow-up actions:
    - **Auto-lint:** Runs a linter on the modified files. If errors are found, it can trigger a "reflection," where the errors are sent back to the LLM in a new request to fix them.
    - **Auto-test:** Runs the configured test command, which can also trigger reflection on failure.
    - **Auto-commit:** If all is well, `auto_commit()` is called. It uses the LLM to generate a commit message based on the conversation and then commits the changes to the git repository.
- The conversation turn is now complete. The messages are moved from `cur_messages` to `done_messages`, the history is summarized in the background, and the system waits for the next user prompt.
