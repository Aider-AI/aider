---
nav_order: 30
---

## Usage

Run `aider` with the source code files you want to edit.
These files will be "added to the chat session", so that the LLM can see their
contents and edit them according to your instructions.

```
aider <file1> <file2> ...
```

Be selective, and just add the files that the LLM will need to edit.
If you add a bunch of unrelated files, the LLM can get overwhelmed
and confused (and it costs more tokens).
Aider will automatically
share snippets from other, related files with the LLM so it can
[understand the rest of your code base](https://aider.chat/docs/repomap.html).

You can also just launch aider anywhere in a git repo without naming files.
You can then add and remove files in the chat
with the `/add` and `/drop` [chat commands](/docs/commands.html).
If you or the LLM mention any of the repo filenames,
aider will ask if you'd like to add them to the chat.

See info about how to [connect to LLMs](/docs/llms.html) for information on
telling aider which model to use.

Aider also has many other options which can be set with
command line switches, environment variables or via a configuration file.

See `aider --help` below for details.

<!--[[[cog
from aider.args import get_help
cog.outl("```")
cog.out(get_help())
cog.outl("```")
]]]-->
```
usage: aider [-h] [--openai-api-key OPENAI_API_KEY] [--anthropic-api-key ANTHROPIC_API_KEY]
             [--model MODEL] [--opus] [--sonnet] [--4] [--4o] [--4-turbo] [--35turbo]
             [--models MODEL] [--openai-api-base OPENAI_API_BASE]
             [--openai-api-type OPENAI_API_TYPE] [--openai-api-version OPENAI_API_VERSION]
             [--openai-api-deployment-id OPENAI_API_DEPLOYMENT_ID]
             [--openai-organization-id OPENAI_ORGANIZATION_ID] [--edit-format EDIT_FORMAT]
             [--weak-model WEAK_MODEL] [--show-model-warnings | --no-show-model-warnings]
             [--map-tokens MAP_TOKENS] [--max-chat-history-tokens MAX_CHAT_HISTORY_TOKENS]
             [--env-file ENV_FILE] [--input-history-file INPUT_HISTORY_FILE]
             [--chat-history-file CHAT_HISTORY_FILE]
             [--restore-chat-history | --no-restore-chat-history] [--dark-mode] [--light-mode]
             [--pretty | --no-pretty] [--stream | --no-stream]
             [--user-input-color USER_INPUT_COLOR] [--tool-output-color TOOL_OUTPUT_COLOR]
             [--tool-error-color TOOL_ERROR_COLOR]
             [--assistant-output-color ASSISTANT_OUTPUT_COLOR] [--code-theme CODE_THEME]
             [--show-diffs] [--git | --no-git] [--gitignore | --no-gitignore]
             [--aiderignore AIDERIGNORE] [--auto-commits | --no-auto-commits]
             [--dirty-commits | --no-dirty-commits] [--dry-run | --no-dry-run] [--commit] [--lint]
             [--lint-cmd LINT_CMD] [--auto-lint | --no-auto-lint] [--test-cmd TEST_CMD]
             [--auto-test | --no-auto-test] [--test] [--voice-language VOICE_LANGUAGE] [--version]
             [--check-update] [--skip-check-update] [--apply FILE] [--yes] [-v] [--show-repo-map]
             [--show-prompts] [--message COMMAND] [--message-file MESSAGE_FILE]
             [--encoding ENCODING] [-c CONFIG_FILE] [--gui]
             [FILE ...]

aider is GPT powered coding in your terminal

options:
  -h, --help            show this help message and exit

Main:
  FILE                  files to edit with an LLM (optional)
  --openai-api-key OPENAI_API_KEY
                        Specify the OpenAI API key [env var: OPENAI_API_KEY]
  --anthropic-api-key ANTHROPIC_API_KEY
                        Specify the OpenAI API key [env var: ANTHROPIC_API_KEY]
  --model MODEL         Specify the model to use for the main chat (default: gpt-4o)
  --opus                Use claude-3-opus-20240229 model for the main chat
  --sonnet              Use claude-3-sonnet-20240229 model for the main chat
  --4, -4               Use gpt-4-0613 model for the main chat
  --4o                  Use gpt-4o model for the main chat
  --4-turbo             Use gpt-4-1106-preview model for the main chat
  --35turbo, --35-turbo, --3, -3
                        Use gpt-3.5-turbo model for the main chat

Model Settings:
  --models MODEL        List known models which match the (partial) MODEL name
  --openai-api-base OPENAI_API_BASE
                        Specify the api base url [env var: OPENAI_API_BASE]
  --openai-api-type OPENAI_API_TYPE
                        Specify the api_type [env var: OPENAI_API_TYPE]
  --openai-api-version OPENAI_API_VERSION
                        Specify the api_version [env var: OPENAI_API_VERSION]
  --openai-api-deployment-id OPENAI_API_DEPLOYMENT_ID
                        Specify the deployment_id [env var: OPENAI_API_DEPLOYMENT_ID]
  --openai-organization-id OPENAI_ORGANIZATION_ID
                        Specify the OpenAI organization ID [env var: OPENAI_ORGANIZATION_ID]
  --edit-format EDIT_FORMAT
                        Specify what edit format the LLM should use (default depends on model)
  --weak-model WEAK_MODEL
                        Specify the model to use for commit messages and chat history
                        summarization (default depends on --model)
  --show-model-warnings, --no-show-model-warnings
                        Only work with models that have meta-data available (default: True)
  --map-tokens MAP_TOKENS
                        Max number of tokens to use for repo map, use 0 to disable (default: 1024)
  --max-chat-history-tokens MAX_CHAT_HISTORY_TOKENS
                        Maximum number of tokens to use for chat history. If not specified, uses
                        the model's max_chat_history_tokens.
  --env-file ENV_FILE   Specify the .env file to load (default: .env in git root)

History Files:
  --input-history-file INPUT_HISTORY_FILE
                        Specify the chat input history file (default: .aider.input.history)
  --chat-history-file CHAT_HISTORY_FILE
                        Specify the chat history file (default: .aider.chat.history.md)
  --restore-chat-history, --no-restore-chat-history
                        Restore the previous chat history messages (default: False)

Output Settings:
  --dark-mode           Use colors suitable for a dark terminal background (default: False)
  --light-mode          Use colors suitable for a light terminal background (default: False)
  --pretty, --no-pretty
                        Enable/disable pretty, colorized output (default: True)
  --stream, --no-stream
                        Enable/disable streaming responses (default: True)
  --user-input-color USER_INPUT_COLOR
                        Set the color for user input (default: #00cc00)
  --tool-output-color TOOL_OUTPUT_COLOR
                        Set the color for tool output (default: None)
  --tool-error-color TOOL_ERROR_COLOR
                        Set the color for tool error messages (default: red)
  --assistant-output-color ASSISTANT_OUTPUT_COLOR
                        Set the color for assistant output (default: #0088ff)
  --code-theme CODE_THEME
                        Set the markdown code theme (default: default, other options include
                        monokai, solarized-dark, solarized-light)
  --show-diffs          Show diffs when committing changes (default: False)

Git Settings:
  --git, --no-git       Enable/disable looking for a git repo (default: True)
  --gitignore, --no-gitignore
                        Enable/disable adding .aider* to .gitignore (default: True)
  --aiderignore AIDERIGNORE
                        Specify the aider ignore file (default: .aiderignore in git root)
  --auto-commits, --no-auto-commits
                        Enable/disable auto commit of LLM changes (default: True)
  --dirty-commits, --no-dirty-commits
                        Enable/disable commits when repo is found dirty (default: True)
  --dry-run, --no-dry-run
                        Perform a dry run without modifying files (default: False)

Fixing and committing:
  --commit              Commit all pending changes with a suitable commit message, then exit
  --lint                Lint and fix provided files, or dirty files if none provided
  --lint-cmd LINT_CMD   Specify lint commands to run for different languages, eg: "python: flake8
                        --select=..." (can be used multiple times)
  --auto-lint, --no-auto-lint
                        Enable/disable automatic linting after changes (default: True)
  --test-cmd TEST_CMD   Specify command to run tests
  --auto-test, --no-auto-test
                        Enable/disable automatic testing after changes (default: False)
  --test                Run tests and fix problems found

Other Settings:
  --voice-language VOICE_LANGUAGE
                        Specify the language for voice using ISO 639-1 code (default: auto)
  --version             Show the version number and exit
  --check-update        Check for updates and return status in the exit code
  --skip-check-update   Skips checking for the update when the program runs
  --apply FILE          Apply the changes from the given file instead of running the chat (debug)
  --yes                 Always say yes to every confirmation
  -v, --verbose         Enable verbose output
  --show-repo-map       Print the repo map and exit (debug)
  --show-prompts        Print the system prompts and exit (debug)
  --message COMMAND, --msg COMMAND, -m COMMAND
                        Specify a single message to send the LLM, process reply then exit
                        (disables chat mode)
  --message-file MESSAGE_FILE, -f MESSAGE_FILE
                        Specify a file containing the message to send the LLM, process reply, then
                        exit (disables chat mode)
  --encoding ENCODING   Specify the encoding for input and output (default: utf-8)
  -c CONFIG_FILE, --config CONFIG_FILE
                        Specify the config file (default: search for .aider.conf.yml in git root,
                        cwd or home directory)
  --gui, --browser      Run aider in your browser

Args that start with '--' can also be set in a config file (specified via -c). The config file
uses YAML syntax and must represent a YAML 'mapping' (for details, see
http://learn.getgrav.org/advanced/yaml). In general, command-line values override environment
variables which override config file values which override defaults.
```
<!--[[[end]]]-->
