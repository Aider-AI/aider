---
parent: Configuration
nav_order: 950
description: Configuring advanced settings for LLMs.
---

# Advanced model settings

## Context window size and token costs

In most cases, you can safely ignore aider's warning about unknown context
window size and model costs.

{: .note }
Aider never *enforces* token limits, it only *reports* token limit errors
from the API provider.
You probably don't need to
configure aider with the proper token limits
for unusual models.

But, you can register context window limits and costs for models that aren't known
to aider. Create a `.aider.model.metadata.json` file in one of these locations:

- Your home directory.
- The root if your git repo.
- The current directory where you launch aider.
- Or specify a specific file with the `--model-metadata-file <filename>` switch.


If the files above exist, they will be loaded in that order. 
Files loaded last will take priority.

The json file should be a dictionary with an entry for each model, as follows:

```
{
    "deepseek/deepseek-chat": {
        "max_tokens": 4096,
        "max_input_tokens": 32000,
        "max_output_tokens": 4096,
        "input_cost_per_token": 0.00000014,
        "output_cost_per_token": 0.00000028,
        "litellm_provider": "deepseek",
        "mode": "chat"
    }
}
```

{: .tip }
Use a fully qualified model name with a `provider/` at the front
in the `.aider.model.metadata.json` file.
For example, use `deepseek/deepseek-chat`, not just `deepseek-chat`.
That prefix should match the `litellm_provider` field.

### Contribute model metadata

Aider relies on
[litellm's model_prices_and_context_window.json file](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) 
for model metadata.

Consider submitting a PR to that file to add missing models.

## Model settings

Aider has a number of settings that control how it works with
different models.
These model settings are pre-configured for most popular models.
But it can sometimes be helpful to override them or add settings for
a model that aider doesn't know about.


### Configuration file locations

You can override or add settings for any model by creating a `.aider.model.settings.yml` file in one of these locations:

- Your home directory.
- The root of your git repo.
- The current directory where you launch aider.
- Or specify a specific file with the `--model-settings-file <filename>` switch.

If the files above exist, they will be loaded in that order. 
Files loaded last will take priority.

The yaml file should be a list of dictionary objects for each model.


### Passing extra params to litellm.completion

The `extra_params` attribute of model settings is used to pass arbitrary
extra parameters to the `litellm.completion()` call when sending data
to the given model.

For example:

```yaml
- name: some-provider/my-special-model
  extra_params:
    extra_headers:
      Custom-Header: value
    max_tokens: 8192
```

You can use the special model name `aider/extra_params` to define 
`extra_params` that will be passed to `litellm.completion()` for all models.
Only the `extra_params` dict is used from this special model name.

For example:

```yaml
- name: aider/extra_params
  extra_params:
    extra_headers:
      Custom-Header: value
    max_tokens: 8192
```

These settings will be merged with any model-specific settings, with the 
`aider/extra_params` settings taking precedence for any direct conflicts.

### Controlling o1 reasoning effort

You need this chunk of yaml:

```
  extra_params:
    extra_body:
      reasoning_effort: high
```

This is a full entry for o1 with that setting, obtained by finding the default
entry in the list below and adding the above `extra_params` entry:

```
- name: o1
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  send_undo_reply: false
  lazy: false
  reminder: user
  examples_as_sys_msg: false
  cache_control: false
  caches_by_default: false
  use_system_prompt: true
  use_temperature: false
  streaming: false
  editor_model_name: gpt-4o
  editor_edit_format: editor-diff
  extra_params:
    extra_body:
      reasoning_effort: high
```

### Default model settings

Below are all the pre-configured model settings to give a sense for the settings which are supported.

You can also look at the `ModelSettings` class in
[models.py](https://github.com/Aider-AI/aider/blob/main/aider/models.py)
file for more details about all of the model setting that aider supports.

The first entry shows all the settings, with their default values.
For a real model,
you just need to include whichever fields that you want to override the defaults.

<!--[[[cog
from aider.models import get_model_settings_as_yaml
cog.out("```yaml\n")
cog.out(get_model_settings_as_yaml())
cog.out("```\n")
]]]-->
```yaml
- name: (default values)
  edit_format: whole
  weak_model_name: null
  use_repo_map: false
  send_undo_reply: false
  lazy: false
  overeager: false
  reminder: user
  examples_as_sys_msg: false
  extra_params: null
  cache_control: false
  caches_by_default: false
  use_system_prompt: true
  use_temperature: true
  streaming: true
  editor_model_name: null
  editor_edit_format: null
  reasoning_tag: null
  remove_reasoning: null
  system_prompt_prefix: null
  accepts_settings: null

- name: anthropic/claude-3-5-haiku-20241022
  edit_format: diff
  weak_model_name: anthropic/claude-3-5-haiku-20241022
  use_repo_map: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
  cache_control: true

- name: anthropic/claude-3-5-sonnet-20240620
  edit_format: diff
  weak_model_name: anthropic/claude-3-5-haiku-20241022
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
    max_tokens: 8192
  cache_control: true
  editor_model_name: anthropic/claude-3-5-sonnet-20240620
  editor_edit_format: editor-diff

- name: anthropic/claude-3-5-sonnet-20241022
  edit_format: diff
  weak_model_name: anthropic/claude-3-5-haiku-20241022
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
    max_tokens: 8192
  cache_control: true
  editor_model_name: anthropic/claude-3-5-sonnet-20241022
  editor_edit_format: editor-diff

- name: anthropic/claude-3-5-sonnet-latest
  edit_format: diff
  weak_model_name: anthropic/claude-3-5-haiku-20241022
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
    max_tokens: 8192
  cache_control: true
  editor_model_name: anthropic/claude-3-5-sonnet-20241022
  editor_edit_format: editor-diff

- name: anthropic/claude-3-7-sonnet-20250219
  edit_format: diff
  weak_model_name: anthropic/claude-3-5-haiku-20241022
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: anthropic/claude-3-7-sonnet-20250219
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: anthropic/claude-3-7-sonnet-latest
  edit_format: diff
  weak_model_name: anthropic/claude-3-5-haiku-20241022
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: anthropic/claude-3-7-sonnet-latest
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: anthropic/claude-3-haiku-20240307
  weak_model_name: anthropic/claude-3-haiku-20240307
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
  cache_control: true

- name: azure/o1
  edit_format: diff
  weak_model_name: azure/gpt-4o-mini
  use_repo_map: true
  use_temperature: false
  streaming: false
  editor_model_name: azure/gpt-4o
  editor_edit_format: editor-diff
  accepts_settings:
  - reasoning_effort

- name: azure/o1-mini
  weak_model_name: azure/gpt-4o-mini
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  editor_model_name: azure/gpt-4o
  editor_edit_format: editor-diff

- name: azure/o1-preview
  edit_format: diff
  weak_model_name: azure/gpt-4o-mini
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  editor_model_name: azure/gpt-4o
  editor_edit_format: editor-diff

- name: azure/o3-mini
  edit_format: diff
  weak_model_name: azure/gpt-4o-mini
  use_repo_map: true
  use_temperature: false
  editor_model_name: azure/gpt-4o
  editor_edit_format: editor-diff
  system_prompt_prefix: 'Formatting re-enabled. '
  accepts_settings:
  - reasoning_effort

- name: bedrock/anthropic.claude-3-5-haiku-20241022-v1:0
  edit_format: diff
  weak_model_name: bedrock/anthropic.claude-3-5-haiku-20241022-v1:0
  use_repo_map: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
  cache_control: true

- name: bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
  edit_format: diff
  weak_model_name: bedrock/anthropic.claude-3-5-haiku-20241022-v1:0
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
    max_tokens: 8192
  cache_control: true
  editor_model_name: bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0
  editor_edit_format: editor-diff

- name: bedrock/anthropic.claude-3-7-sonnet-20250219-v1:0
  edit_format: diff
  weak_model_name: bedrock/anthropic.claude-3-5-haiku-20241022-v1:0
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: bedrock/anthropic.claude-3-7-sonnet-20250219-v1:0
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: bedrock/us.anthropic.claude-3-7-sonnet-20250219-v1:0
  edit_format: diff
  weak_model_name: bedrock/us.anthropic.claude-3-5-haiku-20241022-v1:0
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: bedrock/us.anthropic.claude-3-7-sonnet-20250219-v1:0
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: bedrock_converse/anthropic.claude-3-7-sonnet-20250219-v1:0
  edit_format: diff
  weak_model_name: bedrock_converse/anthropic.claude-3-5-haiku-20241022-v1:0
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: bedrock_converse/anthropic.claude-3-7-sonnet-20250219-v1:0
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: bedrock_converse/us.anthropic.claude-3-7-sonnet-20250219-v1:0
  edit_format: diff
  weak_model_name: bedrock_converse/us.anthropic.claude-3-5-haiku-20241022-v1:0
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: bedrock_converse/us.anthropic.claude-3-7-sonnet-20250219-v1:0
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: claude-3-5-haiku-20241022
  edit_format: diff
  weak_model_name: claude-3-5-haiku-20241022
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
  cache_control: true

- name: claude-3-5-sonnet-20240620
  edit_format: diff
  weak_model_name: claude-3-5-haiku-20241022
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
    max_tokens: 8192
  cache_control: true
  editor_model_name: claude-3-5-sonnet-20240620
  editor_edit_format: editor-diff

- name: claude-3-5-sonnet-20241022
  edit_format: diff
  weak_model_name: claude-3-5-haiku-20241022
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
    max_tokens: 8192
  cache_control: true
  editor_model_name: claude-3-5-sonnet-20241022
  editor_edit_format: editor-diff

- name: claude-3-7-sonnet-20250219
  edit_format: diff
  weak_model_name: claude-3-5-haiku-20241022
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: claude-3-7-sonnet-20250219
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: claude-3-7-sonnet-latest
  edit_format: diff
  weak_model_name: claude-3-5-haiku-20241022
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: claude-3-7-sonnet-latest
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: claude-3-haiku-20240307
  weak_model_name: claude-3-haiku-20240307
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25
  cache_control: true

- name: claude-3-opus-20240229
  edit_format: diff
  weak_model_name: claude-3-5-haiku-20241022
  use_repo_map: true

- name: claude-3-sonnet-20240229
  weak_model_name: claude-3-5-haiku-20241022

- name: cohere_chat/command-a-03-2025
  examples_as_sys_msg: true

- name: command-r-08-2024
  weak_model_name: command-r-08-2024
  use_repo_map: true

- name: command-r-plus
  weak_model_name: command-r-plus
  use_repo_map: true

- name: command-r-plus-08-2024
  weak_model_name: command-r-plus-08-2024
  use_repo_map: true

- name: deepseek-chat
  edit_format: diff
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192

- name: deepseek-coder
  edit_format: diff
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  caches_by_default: true

- name: deepseek/deepseek-chat
  edit_format: diff
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  caches_by_default: true

- name: deepseek/deepseek-coder
  edit_format: diff
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  caches_by_default: true

- name: deepseek/deepseek-reasoner
  edit_format: diff
  weak_model_name: deepseek/deepseek-chat
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  caches_by_default: true
  use_temperature: false
  editor_model_name: deepseek/deepseek-chat
  editor_edit_format: editor-diff

- name: fireworks_ai/accounts/fireworks/models/deepseek-r1
  edit_format: diff
  weak_model_name: fireworks_ai/accounts/fireworks/models/deepseek-v3
  use_repo_map: true
  extra_params:
    max_tokens: 160000
  use_temperature: false
  editor_model_name: fireworks_ai/accounts/fireworks/models/deepseek-v3
  editor_edit_format: editor-diff
  reasoning_tag: think

- name: fireworks_ai/accounts/fireworks/models/deepseek-v3
  edit_format: diff
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 128000

- name: fireworks_ai/accounts/fireworks/models/deepseek-v3-0324
  edit_format: diff
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 160000

- name: fireworks_ai/accounts/fireworks/models/qwq-32b
  edit_format: diff
  weak_model_name: fireworks_ai/accounts/fireworks/models/qwen2p5-coder-32b-instruct
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 32000
    top_p: 0.95
  use_temperature: 0.6
  editor_model_name: fireworks_ai/accounts/fireworks/models/qwen2p5-coder-32b-instruct
  editor_edit_format: editor-diff
  reasoning_tag: think

- name: gemini/gemini-1.5-flash-002

- name: gemini/gemini-1.5-flash-exp-0827

- name: gemini/gemini-1.5-pro
  edit_format: diff-fenced
  use_repo_map: true

- name: gemini/gemini-1.5-pro-002
  edit_format: diff
  use_repo_map: true

- name: gemini/gemini-1.5-pro-exp-0827
  edit_format: diff-fenced
  use_repo_map: true

- name: gemini/gemini-1.5-pro-latest
  edit_format: diff-fenced
  use_repo_map: true

- name: gemini/gemini-2.0-flash
  edit_format: diff
  use_repo_map: true

- name: gemini/gemini-2.0-flash-exp
  edit_format: diff
  use_repo_map: true

- name: gemini/gemini-2.5-pro-exp-03-25
  edit_format: diff-fenced
  weak_model_name: gemini/gemini-2.0-flash
  use_repo_map: true

- name: gemini/gemini-2.5-pro-preview-03-25
  edit_format: diff-fenced
  weak_model_name: gemini/gemini-2.0-flash
  use_repo_map: true

- name: gemini/gemini-exp-1114
  edit_format: diff
  use_repo_map: true

- name: gemini/gemini-exp-1121
  edit_format: diff
  use_repo_map: true

- name: gemini/gemini-exp-1206
  edit_format: diff
  use_repo_map: true

- name: gemini/gemma-3-27b-it
  use_system_prompt: false

- name: gpt-3.5-turbo
  weak_model_name: gpt-4o-mini
  reminder: sys

- name: gpt-3.5-turbo-0125
  weak_model_name: gpt-4o-mini
  reminder: sys

- name: gpt-3.5-turbo-0613
  weak_model_name: gpt-4o-mini
  reminder: sys

- name: gpt-3.5-turbo-1106
  weak_model_name: gpt-4o-mini
  reminder: sys

- name: gpt-3.5-turbo-16k-0613
  weak_model_name: gpt-4o-mini
  reminder: sys

- name: gpt-4-0125-preview
  edit_format: udiff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true

- name: gpt-4-0314
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true

- name: gpt-4-0613
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  reminder: sys

- name: gpt-4-1106-preview
  edit_format: udiff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys

- name: gpt-4-32k-0613
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  reminder: sys

- name: gpt-4-turbo
  edit_format: udiff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys

- name: gpt-4-turbo-2024-04-09
  edit_format: udiff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys

- name: gpt-4-vision-preview
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  reminder: sys

- name: gpt-4.5-preview
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true
  editor_model_name: gpt-4o
  editor_edit_format: editor-diff

- name: gpt-4o
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true
  editor_edit_format: editor-diff

- name: gpt-4o-2024-08-06
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true

- name: gpt-4o-2024-11-20
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true

- name: gpt-4o-mini
  weak_model_name: gpt-4o-mini
  lazy: true
  reminder: sys

- name: groq/llama3-70b-8192
  edit_format: diff
  weak_model_name: groq/llama3-8b-8192
  examples_as_sys_msg: true

- name: groq/qwen-qwq-32b
  edit_format: diff
  weak_model_name: groq/qwen-2.5-coder-32b
  use_repo_map: true
  extra_params:
    max_tokens: 128000
    top_p: 0.95
  use_temperature: 0.6
  editor_model_name: groq/qwen-2.5-coder-32b
  editor_edit_format: editor-diff
  reasoning_tag: think

- name: o1
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  use_temperature: false
  streaming: false
  editor_model_name: gpt-4o
  editor_edit_format: editor-diff
  system_prompt_prefix: 'Formatting re-enabled. '
  accepts_settings:
  - reasoning_effort

- name: o1-mini
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  editor_model_name: gpt-4o
  editor_edit_format: editor-diff

- name: o1-preview
  edit_format: architect
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  editor_model_name: gpt-4o
  editor_edit_format: editor-diff

- name: o3-mini
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  use_temperature: false
  editor_model_name: gpt-4o
  editor_edit_format: editor-diff
  system_prompt_prefix: 'Formatting re-enabled. '
  accepts_settings:
  - reasoning_effort

- name: openai/gpt-4.5-preview
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true
  editor_model_name: openai/gpt-4o
  editor_edit_format: editor-diff

- name: openai/gpt-4o
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true
  editor_edit_format: editor-diff

- name: openai/gpt-4o-2024-08-06
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true

- name: openai/gpt-4o-2024-11-20
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true

- name: openai/gpt-4o-mini
  weak_model_name: openai/gpt-4o-mini
  lazy: true
  reminder: sys

- name: openai/o1
  edit_format: diff
  weak_model_name: openai/gpt-4o-mini
  use_repo_map: true
  use_temperature: false
  streaming: false
  editor_model_name: openai/gpt-4o
  editor_edit_format: editor-diff
  system_prompt_prefix: 'Formatting re-enabled. '
  accepts_settings:
  - reasoning_effort

- name: openai/o1-mini
  weak_model_name: openai/gpt-4o-mini
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  editor_model_name: openai/gpt-4o
  editor_edit_format: editor-diff

- name: openai/o1-preview
  edit_format: diff
  weak_model_name: openai/gpt-4o-mini
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  editor_model_name: openai/gpt-4o
  editor_edit_format: editor-diff

- name: openai/o3-mini
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  use_temperature: false
  editor_model_name: gpt-4o
  editor_edit_format: editor-diff
  system_prompt_prefix: 'Formatting re-enabled. '
  accepts_settings:
  - reasoning_effort

- name: openrouter/anthropic/claude-3-opus
  edit_format: diff
  weak_model_name: openrouter/anthropic/claude-3-5-haiku
  use_repo_map: true

- name: openrouter/anthropic/claude-3.5-sonnet
  edit_format: diff
  weak_model_name: openrouter/anthropic/claude-3-5-haiku
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  cache_control: true
  editor_model_name: openrouter/anthropic/claude-3.5-sonnet
  editor_edit_format: editor-diff

- name: openrouter/anthropic/claude-3.5-sonnet:beta
  edit_format: diff
  weak_model_name: openrouter/anthropic/claude-3-5-haiku:beta
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  cache_control: true
  editor_model_name: openrouter/anthropic/claude-3.5-sonnet:beta
  editor_edit_format: editor-diff

- name: openrouter/anthropic/claude-3.7-sonnet
  edit_format: diff
  weak_model_name: openrouter/anthropic/claude-3-5-haiku
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: openrouter/anthropic/claude-3.7-sonnet
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: openrouter/anthropic/claude-3.7-sonnet:beta
  edit_format: diff
  weak_model_name: openrouter/anthropic/claude-3-5-haiku
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31,pdfs-2024-09-25,output-128k-2025-02-19
    max_tokens: 64000
  cache_control: true
  editor_model_name: openrouter/anthropic/claude-3.7-sonnet
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: openrouter/cohere/command-a-03-2025
  examples_as_sys_msg: true

- name: openrouter/deepseek/deepseek-chat
  edit_format: diff
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true

- name: openrouter/deepseek/deepseek-chat-v3-0324
  edit_format: diff
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  caches_by_default: true

- name: openrouter/deepseek/deepseek-chat-v3-0324:free
  edit_format: diff
  weak_model_name: openrouter/deepseek/deepseek-chat-v3-0324:free
  use_repo_map: true
  examples_as_sys_msg: true
  caches_by_default: true
  use_temperature: false
  editor_model_name: openrouter/deepseek/deepseek-r1:free
  editor_edit_format: editor-diff

- name: openrouter/deepseek/deepseek-chat:free
  edit_format: diff
  weak_model_name: openrouter/deepseek/deepseek-chat:free
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  caches_by_default: true
  use_temperature: false
  editor_model_name: openrouter/deepseek/deepseek-chat:free
  editor_edit_format: editor-diff

- name: openrouter/deepseek/deepseek-coder
  edit_format: diff
  use_repo_map: true
  reminder: sys
  examples_as_sys_msg: true

- name: openrouter/deepseek/deepseek-r1
  edit_format: diff
  weak_model_name: openrouter/deepseek/deepseek-chat
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
    include_reasoning: true
  caches_by_default: true
  editor_model_name: openrouter/deepseek/deepseek-chat
  editor_edit_format: editor-diff

- name: openrouter/deepseek/deepseek-r1-distill-llama-70b
  edit_format: diff
  weak_model_name: openrouter/deepseek/deepseek-chat
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  caches_by_default: true
  use_temperature: false
  editor_model_name: openrouter/deepseek/deepseek-chat
  editor_edit_format: editor-diff

- name: openrouter/deepseek/deepseek-r1:free
  edit_format: diff
  weak_model_name: openrouter/deepseek/deepseek-r1:free
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  caches_by_default: true

- name: openrouter/google/gemini-2.5-pro-exp-03-25:free
  edit_format: diff-fenced
  weak_model_name: openrouter/google/gemini-2.0-flash-exp:free
  use_repo_map: true

- name: openrouter/google/gemma-3-27b-it
  use_system_prompt: false

- name: openrouter/google/gemma-3-27b-it:free
  use_system_prompt: false

- name: openrouter/meta-llama/llama-3-70b-instruct
  edit_format: diff
  weak_model_name: openrouter/meta-llama/llama-3-70b-instruct
  examples_as_sys_msg: true

- name: openrouter/openai/gpt-4o
  edit_format: diff
  weak_model_name: openrouter/openai/gpt-4o-mini
  use_repo_map: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: true
  editor_edit_format: editor-diff

- name: openrouter/openai/o1
  edit_format: diff
  weak_model_name: openrouter/openai/gpt-4o-mini
  use_repo_map: true
  use_temperature: false
  streaming: false
  editor_model_name: openrouter/openai/gpt-4o
  editor_edit_format: editor-diff
  system_prompt_prefix: 'Formatting re-enabled. '
  accepts_settings:
  - reasoning_effort

- name: openrouter/openai/o1-mini
  weak_model_name: openrouter/openai/gpt-4o-mini
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  streaming: false
  editor_model_name: openrouter/openai/gpt-4o
  editor_edit_format: editor-diff

- name: openrouter/openai/o1-preview
  edit_format: diff
  weak_model_name: openrouter/openai/gpt-4o-mini
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  streaming: false
  editor_model_name: openrouter/openai/gpt-4o
  editor_edit_format: editor-diff

- name: openrouter/openai/o3-mini
  edit_format: diff
  weak_model_name: openrouter/openai/gpt-4o-mini
  use_repo_map: true
  use_temperature: false
  editor_model_name: openrouter/openai/gpt-4o
  editor_edit_format: editor-diff
  system_prompt_prefix: 'Formatting re-enabled. '
  accepts_settings:
  - reasoning_effort

- name: openrouter/openai/o3-mini-high
  edit_format: diff
  weak_model_name: openrouter/openai/gpt-4o-mini
  use_repo_map: true
  use_temperature: false
  editor_model_name: openrouter/openai/gpt-4o
  editor_edit_format: editor-diff
  system_prompt_prefix: 'Formatting re-enabled. '
  accepts_settings:
  - reasoning_effort

- name: openrouter/openrouter/optimus-alpha
  edit_format: diff
  use_repo_map: true
  examples_as_sys_msg: true

- name: openrouter/openrouter/quasar-alpha
  edit_format: diff
  use_repo_map: true
  examples_as_sys_msg: true

- name: openrouter/qwen/qwen-2.5-coder-32b-instruct
  edit_format: diff
  weak_model_name: openrouter/qwen/qwen-2.5-coder-32b-instruct
  use_repo_map: true
  editor_model_name: openrouter/qwen/qwen-2.5-coder-32b-instruct
  editor_edit_format: editor-diff

- name: openrouter/x-ai/grok-3-beta
  edit_format: diff
  use_repo_map: true

- name: openrouter/x-ai/grok-3-mini-beta
  use_repo_map: true
  accepts_settings:
  - reasoning_effort

- name: vertex_ai-anthropic_models/vertex_ai/claude-3-7-sonnet@20250219
  edit_format: diff
  weak_model_name: vertex_ai/claude-3-5-haiku@20241022
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 64000
  editor_model_name: vertex_ai-anthropic_models/vertex_ai/claude-3-7-sonnet@20250219
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: vertex_ai/claude-3-5-haiku@20241022
  edit_format: diff
  weak_model_name: vertex_ai/claude-3-5-haiku@20241022
  use_repo_map: true
  extra_params:
    max_tokens: 4096

- name: vertex_ai/claude-3-5-sonnet-v2@20241022
  edit_format: diff
  weak_model_name: vertex_ai/claude-3-5-haiku@20241022
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  editor_model_name: vertex_ai/claude-3-5-sonnet-v2@20241022
  editor_edit_format: editor-diff

- name: vertex_ai/claude-3-5-sonnet@20240620
  edit_format: diff
  weak_model_name: vertex_ai/claude-3-5-haiku@20241022
  use_repo_map: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  editor_model_name: vertex_ai/claude-3-5-sonnet@20240620
  editor_edit_format: editor-diff

- name: vertex_ai/claude-3-7-sonnet@20250219
  edit_format: diff
  weak_model_name: vertex_ai/claude-3-5-haiku@20241022
  use_repo_map: true
  overeager: true
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 64000
  editor_model_name: vertex_ai/claude-3-7-sonnet@20250219
  editor_edit_format: editor-diff
  accepts_settings:
  - thinking_tokens

- name: vertex_ai/claude-3-opus@20240229
  edit_format: diff
  weak_model_name: vertex_ai/claude-3-5-haiku@20241022
  use_repo_map: true

- name: vertex_ai/claude-3-sonnet@20240229
  weak_model_name: vertex_ai/claude-3-5-haiku@20241022

- name: vertex_ai/gemini-2.5-pro-exp-03-25
  edit_format: diff-fenced
  use_repo_map: true

- name: vertex_ai/gemini-2.5-pro-preview-03-25
  edit_format: diff-fenced
  use_repo_map: true

- name: vertex_ai/gemini-pro-experimental
  edit_format: diff-fenced
  use_repo_map: true

- name: xai/grok-3-beta
  edit_format: diff
  use_repo_map: true

- name: xai/grok-3-mini-beta
  use_repo_map: true
  accepts_settings:
  - reasoning_effort
```
<!--[[[end]]]-->


