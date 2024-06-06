---
parent: Configuration
nav_order: 15
---

## Using `.aider.conf.yml`

Most options can also be set in an `.aider.conf.yml` file
which can be placed in your home directory or at the root of
your git repo. 

Below is a sample of the file, which you
can also
[download from GitHub](https://github.com/paul-gauthier/aider/blob/main/website/assets/sample.aider.conf.yml).

<!--[[[cog
from aider.args import get_sample_yaml
from pathlib import Path
text=get_sample_yaml()
Path("website/assets/sample.aider.conf.yml").write_text(text)
cog.outl("```")
cog.out(text)
cog.outl("```")
]]]-->
```
##########################################################
# Sample .aider.conf.yaml
# Place in your home dir, or at the root of your git repo.
##########################################################

##########
# options:

## show this help message and exit
#help: 

#######
# Main:

## files to edit with an LLM (optional)
#files: 

## Specify the OpenAI API key
#openai_api_key: 

## Specify the OpenAI API key
#anthropic_api_key: 

## Specify the model to use for the main chat (default: gpt-4o)
#model: gpt-4o

## Use claude-3-opus-20240229 model for the main chat
#model: claude-3-opus-20240229

## Use claude-3-sonnet-20240229 model for the main chat
#model: claude-3-sonnet-20240229

## Use gpt-4-0613 model for the main chat
#model: gpt-4-0613

## Use gpt-4o model for the main chat
#model: gpt-4o

## Use gpt-4-1106-preview model for the main chat
#model: gpt-4-1106-preview

## Use gpt-3.5-turbo model for the main chat
#model: gpt-3.5-turbo

#################
# Model Settings:

## List known models which match the (partial) MODEL name
#models: 

## Specify the api base url
#openai_api_base: 

## Specify the api_type
#openai_api_type: 

## Specify the api_version
#openai_api_version: 

## Specify the deployment_id
#openai_api_deployment_id: 

## Specify the OpenAI organization ID
#openai_organization_id: 

## Specify what edit format the LLM should use (default depends on model)
#edit_format: 

## Specify the model to use for commit messages and chat history summarization (default depends on --model)
#weak_model: 

## Only work with models that have meta-data available (default: True)
#show_model_warnings: true

## Max number of tokens to use for repo map, use 0 to disable (default: 1024)
#map_tokens: true

## Maximum number of tokens to use for chat history. If not specified, uses the model's max_chat_history_tokens.
#max_chat_history_tokens: 

## Specify the .env file to load (default: .env in git root)
#env_file: .env

################
# History Files:

## Specify the chat input history file (default: .aider.input.history)
#input_history_file: .aider.input.history

## Specify the chat history file (default: .aider.chat.history.md)
#chat_history_file: .aider.chat.history.md

## Restore the previous chat history messages (default: False)
#restore_chat_history: false

##################
# Output Settings:

## Use colors suitable for a dark terminal background (default: False)
#dark_mode: false

## Use colors suitable for a light terminal background (default: False)
#light_mode: false

## Enable/disable pretty, colorized output (default: True)
#pretty: true

## Enable/disable streaming responses (default: True)
#stream: true

## Set the color for user input (default: #00cc00)
#user_input_color: #00cc00

## Set the color for tool output (default: None)
#tool_output_color: 

## Set the color for tool error messages (default: red)
#tool_error_color: #FF2222

## Set the color for assistant output (default: #0088ff)
#assistant_output_color: #0088ff

## Set the markdown code theme (default: default, other options include monokai, solarized-dark, solarized-light)
#code_theme: default

## Show diffs when committing changes (default: False)
#show_diffs: false

###############
# Git Settings:

## Enable/disable looking for a git repo (default: True)
#git: true

## Enable/disable adding .aider* to .gitignore (default: True)
#gitignore: true

## Specify the aider ignore file (default: .aiderignore in git root)
#aiderignore: .aiderignore

## Enable/disable auto commit of LLM changes (default: True)
#auto_commits: true

## Enable/disable commits when repo is found dirty (default: True)
#dirty_commits: true

## Perform a dry run without modifying files (default: False)
#dry_run: false

########################
# Fixing and committing:

## Commit all pending changes with a suitable commit message, then exit
#commit: false

## Lint and fix provided files, or dirty files if none provided
#lint: false

## Specify lint commands to run for different languages, eg: "python: flake8 --select=..." (can be used multiple times)
#lint_cmd: 

## Enable/disable automatic linting after changes (default: True)
#auto_lint: true

## Specify command to run tests
#test_cmd: 

## Enable/disable automatic testing after changes (default: False)
#auto_test: false

## Run tests and fix problems found
#test: false

#################
# Other Settings:

## Specify the language for voice using ISO 639-1 code (default: auto)
#voice_language: en

## Show the version number and exit
#version: 

## Check for updates and return status in the exit code
#check_update: false

## Skips checking for the update when the program runs
#skip_check_update: false

## Apply the changes from the given file instead of running the chat (debug)
#apply: 

## Always say yes to every confirmation
#yes: false

## Enable verbose output
#verbose: false

## Print the repo map and exit (debug)
#show_repo_map: false

## Print the system prompts and exit (debug)
#show_prompts: false

## Specify a single message to send the LLM, process reply then exit (disables chat mode)
#message: 

## Specify a file containing the message to send the LLM, process reply, then exit (disables chat mode)
#message_file: 

## Specify the encoding for input and output (default: utf-8)
#encoding: utf-8

## Specify the config file (default: search for .aider.conf.yml in git root, cwd or home directory)
#config: 

## Run aider in your browser
#gui: false
```
<!--[[[end]]]-->
