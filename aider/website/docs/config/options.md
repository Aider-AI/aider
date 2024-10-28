---
parent: Configuration
nav_order: 10
description: Details about all of aider's settings.
---

# Options reference
{: .no_toc }

You can use `aider --help` to see all the available options,
or review them below.

- TOC
{:toc}

## LLM keys
{: .no_toc }

{% include special-keys.md %}

## Usage summary

<!--[[[cog
from aider.args import get_md_help
cog.out(get_md_help())
]]]-->
```
usage: aider [-h] [--openai-api-key] [--anthropic-api-key] [--model]
             [--opus] [--sonnet] [--4] [--4o] [--mini] [--4-turbo]
             [--35turbo] [--deepseek] [--o1-mini] [--o1-preview]
             [--list-models] [--openai-api-base] [--openai-api-type]
             [--openai-api-version] [--openai-api-deployment-id]
             [--openai-organization-id] [--model-settings-file]
             [--model-metadata-file]
             [--verify-ssl | --no-verify-ssl] [--edit-format]
             [--architect] [--weak-model] [--editor-model]
             [--editor-edit-format]
             [--show-model-warnings | --no-show-model-warnings]
             [--max-chat-history-tokens] [--env-file]
             [--cache-prompts | --no-cache-prompts]
             [--cache-keepalive-pings] [--map-tokens]
             [--map-refresh] [--map-multiplier-no-files]
             [--input-history-file] [--chat-history-file]
             [--restore-chat-history | --no-restore-chat-history]
             [--llm-history-file] [--dark-mode] [--light-mode]
             [--pretty | --no-pretty] [--stream | --no-stream]
             [--user-input-color] [--tool-output-color]
             [--tool-error-color] [--tool-warning-color]
             [--assistant-output-color] [--completion-menu-color]
             [--completion-menu-bg-color]
             [--completion-menu-current-color]
             [--completion-menu-current-bg-color] [--code-theme]
             [--show-diffs] [--git | --no-git]
             [--gitignore | --no-gitignore] [--aiderignore]
             [--subtree-only] [--auto-commits | --no-auto-commits]
             [--dirty-commits | --no-dirty-commits]
             [--attribute-author | --no-attribute-author]
             [--attribute-committer | --no-attribute-committer]
             [--attribute-commit-message-author | --no-attribute-commit-message-author]
             [--attribute-commit-message-committer | --no-attribute-commit-message-committer]
             [--commit] [--commit-prompt] [--dry-run | --no-dry-run]
             [--skip-sanity-check-repo] [--lint] [--lint-cmd]
             [--auto-lint | --no-auto-lint] [--test-cmd]
             [--auto-test | --no-auto-test] [--test] [--file]
             [--read] [--vim] [--chat-language] [--version]
             [--just-check-update]
             [--check-update | --no-check-update]
             [--install-main-branch] [--upgrade] [--apply]
             [--yes-always] [-v] [--show-repo-map] [--show-prompts]
             [--exit] [--message] [--message-file] [--encoding] [-c]
             [--gui]
             [--suggest-shell-commands | --no-suggest-shell-commands]
             [--fancy-input | --no-fancy-input] [--voice-format]
             [--voice-language]

```

## options:

### `--help`
show this help message and exit  
Aliases:
  - `-h`
  - `--help`

## Main:

### `--openai-api-key OPENAI_API_KEY`
Specify the OpenAI API key  
Environment variable: `OPENAI_API_KEY`  

### `--anthropic-api-key ANTHROPIC_API_KEY`
Specify the Anthropic API key  
Environment variable: `ANTHROPIC_API_KEY`  

### `--model MODEL`
Specify the model to use for the main chat  
Environment variable: `AIDER_MODEL`  

### `--opus`
Use claude-3-opus-20240229 model for the main chat  
Environment variable: `AIDER_OPUS`  

### `--sonnet`
Use claude-3-5-sonnet-20241022 model for the main chat  
Environment variable: `AIDER_SONNET`  

### `--4`
Use gpt-4-0613 model for the main chat  
Environment variable: `AIDER_4`  
Aliases:
  - `--4`
  - `-4`

### `--4o`
Use gpt-4o-2024-08-06 model for the main chat  
Environment variable: `AIDER_4O`  

### `--mini`
Use gpt-4o-mini model for the main chat  
Environment variable: `AIDER_MINI`  

### `--4-turbo`
Use gpt-4-1106-preview model for the main chat  
Environment variable: `AIDER_4_TURBO`  

### `--35turbo`
Use gpt-3.5-turbo model for the main chat  
Environment variable: `AIDER_35TURBO`  
Aliases:
  - `--35turbo`
  - `--35-turbo`
  - `--3`
  - `-3`

### `--deepseek`
Use deepseek/deepseek-coder model for the main chat  
Environment variable: `AIDER_DEEPSEEK`  

### `--o1-mini`
Use o1-mini model for the main chat  
Environment variable: `AIDER_O1_MINI`  

### `--o1-preview`
Use o1-preview model for the main chat  
Environment variable: `AIDER_O1_PREVIEW`  

## Model Settings:

### `--list-models MODEL`
List known models which match the (partial) MODEL name  
Environment variable: `AIDER_LIST_MODELS`  
Aliases:
  - `--list-models MODEL`
  - `--models MODEL`

### `--openai-api-base OPENAI_API_BASE`
Specify the api base url  
Environment variable: `OPENAI_API_BASE`  

### `--openai-api-type OPENAI_API_TYPE`
Specify the api_type  
Environment variable: `OPENAI_API_TYPE`  

### `--openai-api-version OPENAI_API_VERSION`
Specify the api_version  
Environment variable: `OPENAI_API_VERSION`  

### `--openai-api-deployment-id OPENAI_API_DEPLOYMENT_ID`
Specify the deployment_id  
Environment variable: `OPENAI_API_DEPLOYMENT_ID`  

### `--openai-organization-id OPENAI_ORGANIZATION_ID`
Specify the OpenAI organization ID  
Environment variable: `OPENAI_ORGANIZATION_ID`  

### `--model-settings-file MODEL_SETTINGS_FILE`
Specify a file with aider model settings for unknown models  
Default: .aider.model.settings.yml  
Environment variable: `AIDER_MODEL_SETTINGS_FILE`  

### `--model-metadata-file MODEL_METADATA_FILE`
Specify a file with context window and costs for unknown models  
Default: .aider.model.metadata.json  
Environment variable: `AIDER_MODEL_METADATA_FILE`  

### `--verify-ssl`
Verify the SSL cert when connecting to models (default: True)  
Default: True  
Environment variable: `AIDER_VERIFY_SSL`  
Aliases:
  - `--verify-ssl`
  - `--no-verify-ssl`

### `--edit-format EDIT_FORMAT`
Specify what edit format the LLM should use (default depends on model)  
Environment variable: `AIDER_EDIT_FORMAT`  
Aliases:
  - `--edit-format EDIT_FORMAT`
  - `--chat-mode EDIT_FORMAT`

### `--architect`
Use architect edit format for the main chat  
Environment variable: `AIDER_ARCHITECT`  

### `--weak-model WEAK_MODEL`
Specify the model to use for commit messages and chat history summarization (default depends on --model)  
Environment variable: `AIDER_WEAK_MODEL`  

### `--editor-model EDITOR_MODEL`
Specify the model to use for editor tasks (default depends on --model)  
Environment variable: `AIDER_EDITOR_MODEL`  

### `--editor-edit-format EDITOR_EDIT_FORMAT`
Specify the edit format for the editor model (default: depends on editor model)  
Environment variable: `AIDER_EDITOR_EDIT_FORMAT`  

### `--show-model-warnings`
Only work with models that have meta-data available (default: True)  
Default: True  
Environment variable: `AIDER_SHOW_MODEL_WARNINGS`  
Aliases:
  - `--show-model-warnings`
  - `--no-show-model-warnings`

### `--max-chat-history-tokens VALUE`
Soft limit on tokens for chat history, after which summarization begins. If unspecified, defaults to the model's max_chat_history_tokens.  
Environment variable: `AIDER_MAX_CHAT_HISTORY_TOKENS`  

### `--env-file ENV_FILE`
Specify the .env file to load (default: .env in git root)  
Default: .env  
Environment variable: `AIDER_ENV_FILE`  

## Cache Settings:

### `--cache-prompts`
Enable caching of prompts (default: False)  
Default: False  
Environment variable: `AIDER_CACHE_PROMPTS`  
Aliases:
  - `--cache-prompts`
  - `--no-cache-prompts`

### `--cache-keepalive-pings VALUE`
Number of times to ping at 5min intervals to keep prompt cache warm (default: 0)  
Default: 0  
Environment variable: `AIDER_CACHE_KEEPALIVE_PINGS`  

## Repomap Settings:

### `--map-tokens VALUE`
Suggested number of tokens to use for repo map, use 0 to disable (default: 1024)  
Environment variable: `AIDER_MAP_TOKENS`  

### `--map-refresh VALUE`
Control how often the repo map is refreshed. Options: auto, always, files, manual (default: auto)  
Default: auto  
Environment variable: `AIDER_MAP_REFRESH`  

### `--map-multiplier-no-files VALUE`
Multiplier for map tokens when no files are specified (default: 2)  
Default: 2  
Environment variable: `AIDER_MAP_MULTIPLIER_NO_FILES`  

## History Files:

### `--input-history-file INPUT_HISTORY_FILE`
Specify the chat input history file (default: .aider.input.history)  
Default: .aider.input.history  
Environment variable: `AIDER_INPUT_HISTORY_FILE`  

### `--chat-history-file CHAT_HISTORY_FILE`
Specify the chat history file (default: .aider.chat.history.md)  
Default: .aider.chat.history.md  
Environment variable: `AIDER_CHAT_HISTORY_FILE`  

### `--restore-chat-history`
Restore the previous chat history messages (default: False)  
Default: False  
Environment variable: `AIDER_RESTORE_CHAT_HISTORY`  
Aliases:
  - `--restore-chat-history`
  - `--no-restore-chat-history`

### `--llm-history-file LLM_HISTORY_FILE`
Log the conversation with the LLM to this file (for example, .aider.llm.history)  
Environment variable: `AIDER_LLM_HISTORY_FILE`  

## Output Settings:

### `--dark-mode`
Use colors suitable for a dark terminal background (default: False)  
Default: False  
Environment variable: `AIDER_DARK_MODE`  

### `--light-mode`
Use colors suitable for a light terminal background (default: False)  
Default: False  
Environment variable: `AIDER_LIGHT_MODE`  

### `--pretty`
Enable/disable pretty, colorized output (default: True)  
Default: True  
Environment variable: `AIDER_PRETTY`  
Aliases:
  - `--pretty`
  - `--no-pretty`

### `--stream`
Enable/disable streaming responses (default: True)  
Default: True  
Environment variable: `AIDER_STREAM`  
Aliases:
  - `--stream`
  - `--no-stream`

### `--user-input-color VALUE`
Set the color for user input (default: #00cc00)  
Default: #00cc00  
Environment variable: `AIDER_USER_INPUT_COLOR`  

### `--tool-output-color VALUE`
Set the color for tool output (default: None)  
Environment variable: `AIDER_TOOL_OUTPUT_COLOR`  

### `--tool-error-color VALUE`
Set the color for tool error messages (default: #FF2222)  
Default: #FF2222  
Environment variable: `AIDER_TOOL_ERROR_COLOR`  

### `--tool-warning-color VALUE`
Set the color for tool warning messages (default: #FFA500)  
Default: #FFA500  
Environment variable: `AIDER_TOOL_WARNING_COLOR`  

### `--assistant-output-color VALUE`
Set the color for assistant output (default: #0088ff)  
Default: #0088ff  
Environment variable: `AIDER_ASSISTANT_OUTPUT_COLOR`  

### `--completion-menu-color COLOR`
Set the color for the completion menu (default: terminal's default text color)  
Environment variable: `AIDER_COMPLETION_MENU_COLOR`  

### `--completion-menu-bg-color COLOR`
Set the background color for the completion menu (default: terminal's default background color)  
Environment variable: `AIDER_COMPLETION_MENU_BG_COLOR`  

### `--completion-menu-current-color COLOR`
Set the color for the current item in the completion menu (default: terminal's default background color)  
Environment variable: `AIDER_COMPLETION_MENU_CURRENT_COLOR`  

### `--completion-menu-current-bg-color COLOR`
Set the background color for the current item in the completion menu (default: terminal's default text color)  
Environment variable: `AIDER_COMPLETION_MENU_CURRENT_BG_COLOR`  

### `--code-theme VALUE`
Set the markdown code theme (default: default, other options include monokai, solarized-dark, solarized-light)  
Default: default  
Environment variable: `AIDER_CODE_THEME`  

### `--show-diffs`
Show diffs when committing changes (default: False)  
Default: False  
Environment variable: `AIDER_SHOW_DIFFS`  

## Git Settings:

### `--git`
Enable/disable looking for a git repo (default: True)  
Default: True  
Environment variable: `AIDER_GIT`  
Aliases:
  - `--git`
  - `--no-git`

### `--gitignore`
Enable/disable adding .aider* to .gitignore (default: True)  
Default: True  
Environment variable: `AIDER_GITIGNORE`  
Aliases:
  - `--gitignore`
  - `--no-gitignore`

### `--aiderignore AIDERIGNORE`
Specify the aider ignore file (default: .aiderignore in git root)  
Default: .aiderignore  
Environment variable: `AIDER_AIDERIGNORE`  

### `--subtree-only`
Only consider files in the current subtree of the git repository  
Default: False  
Environment variable: `AIDER_SUBTREE_ONLY`  

### `--auto-commits`
Enable/disable auto commit of LLM changes (default: True)  
Default: True  
Environment variable: `AIDER_AUTO_COMMITS`  
Aliases:
  - `--auto-commits`
  - `--no-auto-commits`

### `--dirty-commits`
Enable/disable commits when repo is found dirty (default: True)  
Default: True  
Environment variable: `AIDER_DIRTY_COMMITS`  
Aliases:
  - `--dirty-commits`
  - `--no-dirty-commits`

### `--attribute-author`
Attribute aider code changes in the git author name (default: True)  
Default: True  
Environment variable: `AIDER_ATTRIBUTE_AUTHOR`  
Aliases:
  - `--attribute-author`
  - `--no-attribute-author`

### `--attribute-committer`
Attribute aider commits in the git committer name (default: True)  
Default: True  
Environment variable: `AIDER_ATTRIBUTE_COMMITTER`  
Aliases:
  - `--attribute-committer`
  - `--no-attribute-committer`

### `--attribute-commit-message-author`
Prefix commit messages with 'aider: ' if aider authored the changes (default: False)  
Default: False  
Environment variable: `AIDER_ATTRIBUTE_COMMIT_MESSAGE_AUTHOR`  
Aliases:
  - `--attribute-commit-message-author`
  - `--no-attribute-commit-message-author`

### `--attribute-commit-message-committer`
Prefix all commit messages with 'aider: ' (default: False)  
Default: False  
Environment variable: `AIDER_ATTRIBUTE_COMMIT_MESSAGE_COMMITTER`  
Aliases:
  - `--attribute-commit-message-committer`
  - `--no-attribute-commit-message-committer`

### `--commit`
Commit all pending changes with a suitable commit message, then exit  
Default: False  
Environment variable: `AIDER_COMMIT`  

### `--commit-prompt PROMPT`
Specify a custom prompt for generating commit messages  
Environment variable: `AIDER_COMMIT_PROMPT`  

### `--dry-run`
Perform a dry run without modifying files (default: False)  
Default: False  
Environment variable: `AIDER_DRY_RUN`  
Aliases:
  - `--dry-run`
  - `--no-dry-run`

### `--skip-sanity-check-repo`
Skip the sanity check for the git repository (default: False)  
Default: False  
Environment variable: `AIDER_SKIP_SANITY_CHECK_REPO`  

## Fixing and committing:

### `--lint`
Lint and fix provided files, or dirty files if none provided  
Default: False  
Environment variable: `AIDER_LINT`  

### `--lint-cmd`
Specify lint commands to run for different languages, eg: "python: flake8 --select=..." (can be used multiple times)  
Default: []  
Environment variable: `AIDER_LINT_CMD`  

### `--auto-lint`
Enable/disable automatic linting after changes (default: True)  
Default: True  
Environment variable: `AIDER_AUTO_LINT`  
Aliases:
  - `--auto-lint`
  - `--no-auto-lint`

### `--test-cmd VALUE`
Specify command to run tests  
Default: []  
Environment variable: `AIDER_TEST_CMD`  

### `--auto-test`
Enable/disable automatic testing after changes (default: False)  
Default: False  
Environment variable: `AIDER_AUTO_TEST`  
Aliases:
  - `--auto-test`
  - `--no-auto-test`

### `--test`
Run tests and fix problems found  
Default: False  
Environment variable: `AIDER_TEST`  

## Other Settings:

### `--file FILE`
specify a file to edit (can be used multiple times)  
Environment variable: `AIDER_FILE`  

### `--read FILE`
specify a read-only file (can be used multiple times)  
Environment variable: `AIDER_READ`  

### `--vim`
Use VI editing mode in the terminal (default: False)  
Default: False  
Environment variable: `AIDER_VIM`  

### `--chat-language CHAT_LANGUAGE`
Specify the language to use in the chat (default: None, uses system settings)  
Environment variable: `AIDER_CHAT_LANGUAGE`  

### `--version`
Show the version number and exit  

### `--just-check-update`
Check for updates and return status in the exit code  
Default: False  
Environment variable: `AIDER_JUST_CHECK_UPDATE`  

### `--check-update`
Check for new aider versions on launch  
Default: True  
Environment variable: `AIDER_CHECK_UPDATE`  
Aliases:
  - `--check-update`
  - `--no-check-update`

### `--install-main-branch`
Install the latest version from the main branch  
Default: False  
Environment variable: `AIDER_INSTALL_MAIN_BRANCH`  

### `--upgrade`
Upgrade aider to the latest version from PyPI  
Default: False  
Environment variable: `AIDER_UPGRADE`  
Aliases:
  - `--upgrade`
  - `--update`

### `--apply FILE`
Apply the changes from the given file instead of running the chat (debug)  
Environment variable: `AIDER_APPLY`  

### `--yes-always`
Always say yes to every confirmation  
Environment variable: `AIDER_YES_ALWAYS`  

### `--verbose`
Enable verbose output  
Default: False  
Environment variable: `AIDER_VERBOSE`  
Aliases:
  - `-v`
  - `--verbose`

### `--show-repo-map`
Print the repo map and exit (debug)  
Default: False  
Environment variable: `AIDER_SHOW_REPO_MAP`  

### `--show-prompts`
Print the system prompts and exit (debug)  
Default: False  
Environment variable: `AIDER_SHOW_PROMPTS`  

### `--exit`
Do all startup activities then exit before accepting user input (debug)  
Default: False  
Environment variable: `AIDER_EXIT`  

### `--message COMMAND`
Specify a single message to send the LLM, process reply then exit (disables chat mode)  
Environment variable: `AIDER_MESSAGE`  
Aliases:
  - `--message COMMAND`
  - `--msg COMMAND`
  - `-m COMMAND`

### `--message-file MESSAGE_FILE`
Specify a file containing the message to send the LLM, process reply, then exit (disables chat mode)  
Environment variable: `AIDER_MESSAGE_FILE`  
Aliases:
  - `--message-file MESSAGE_FILE`
  - `-f MESSAGE_FILE`

### `--encoding VALUE`
Specify the encoding for input and output (default: utf-8)  
Default: utf-8  
Environment variable: `AIDER_ENCODING`  

### `--config CONFIG_FILE`
Specify the config file (default: search for .aider.conf.yml in git root, cwd or home directory)  
Aliases:
  - `-c CONFIG_FILE`
  - `--config CONFIG_FILE`

### `--gui`
Run aider in your browser  
Default: False  
Environment variable: `AIDER_GUI`  
Aliases:
  - `--gui`
  - `--browser`

### `--suggest-shell-commands`
Enable/disable suggesting shell commands (default: True)  
Default: True  
Environment variable: `AIDER_SUGGEST_SHELL_COMMANDS`  
Aliases:
  - `--suggest-shell-commands`
  - `--no-suggest-shell-commands`

### `--fancy-input`
Enable/disable fancy input with history and completion (default: True)  
Default: True  
Environment variable: `AIDER_FANCY_INPUT`  
Aliases:
  - `--fancy-input`
  - `--no-fancy-input`

## Voice Settings:

### `--voice-format VOICE_FORMAT`
Audio format for voice recording (default: wav). webm and mp3 require ffmpeg  
Default: wav  
Environment variable: `AIDER_VOICE_FORMAT`  

### `--voice-language VOICE_LANGUAGE`
Specify the language for voice using ISO 639-1 code (default: auto)  
Default: en  
Environment variable: `AIDER_VOICE_LANGUAGE`  
<!--[[[end]]]-->
