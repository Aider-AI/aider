---
parent: Configuration
nav_order: 950
description: Configuring advanced settings for LLMs.
---

# Advanced model settings

## Context window size and token costs

In most cases, you can safely ignore aider's warning about unknown context
window size and model costs.

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

See 
[litellm's model_prices_and_context_window.json file](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) for more examples.

{: .tip }
Use a fully qualified model name with a `provider/` at the front
in the `.aider.model.metadata.json` file.
For example, use `deepseek/deepseek-chat`, not just `deepseek-chat`.

## Model settings

Aider has a number of settings that control how it works with
different models.
These model settings are pre-configured for most popular models.
But it can sometimes be helpful to override them or add settings for
a model that aider doesn't know about.

To do that,
create a `.aider.model.settings.yml` file in one of these locations:

- Your home directory.
- The root if your git repo.
- The current directory where you launch aider.
- Or specify a specific file with the `--model-settings-file <filename>` switch.

If the files above exist, they will be loaded in that order. 
Files loaded last will take priority.

The yaml file should be a a list of dictionary objects for each model.
For example, below are all the pre-configured model settings
to give a sense for the settings which are supported.

You can also look at the `ModelSettings` class in
[models.py](https://github.com/Aider-AI/aider/blob/main/aider/models.py)
file for more details about all of the model setting that aider supports.

<!--[[[cog
from aider.models import get_model_settings_as_yaml
cog.out("```yaml\n")
cog.out(get_model_settings_as_yaml())
cog.out("```\n")
]]]-->
```yaml
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gpt-3.5-turbo
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gpt-3.5-turbo-0125
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gpt-3.5-turbo-1106
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gpt-3.5-turbo-0613
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gpt-3.5-turbo-16k-0613
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: udiff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: gpt-4-turbo-2024-04-09
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: udiff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: gpt-4-turbo
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: openai/gpt-4o
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: openai/gpt-4o-2024-08-06
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: gpt-4o-2024-08-06
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: gpt-4o
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: gpt-4o-mini
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: openai/gpt-4o-mini
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openai/gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: udiff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params: null
  lazy: true
  name: gpt-4-0125-preview
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: udiff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: gpt-4-1106-preview
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gpt-4-vision-preview
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params: null
  lazy: false
  name: gpt-4-0314
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gpt-4-0613
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gpt-4-32k-0613
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: claude-3-opus-20240229
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: openrouter/anthropic/claude-3-opus
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openrouter/anthropic/claude-3-haiku
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: claude-3-sonnet-20240229
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- cache_control: true
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: claude-3-5-sonnet-20240620
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31
    max_tokens: 8192
  lazy: false
  name: claude-3-5-sonnet-20240620
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- cache_control: true
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: anthropic/claude-3-5-sonnet-20240620
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31
    max_tokens: 8192
  lazy: false
  name: anthropic/claude-3-5-sonnet-20240620
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: anthropic/claude-3-haiku-20240307
- cache_control: true
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: anthropic/claude-3-5-sonnet-20241022
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31
    max_tokens: 8192
  lazy: false
  name: anthropic/claude-3-5-sonnet-20241022
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: anthropic/claude-3-haiku-20240307
- cache_control: true
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: claude-3-5-sonnet-20241022
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31
    max_tokens: 8192
  lazy: false
  name: claude-3-5-sonnet-20241022
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- cache_control: true
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31
  lazy: false
  name: anthropic/claude-3-haiku-20240307
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: anthropic/claude-3-haiku-20240307
- cache_control: true
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params:
    extra_headers:
      anthropic-beta: prompt-caching-2024-07-31
  lazy: false
  name: claude-3-haiku-20240307
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- cache_control: true
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: openrouter/anthropic/claude-3.5-sonnet
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  lazy: false
  name: openrouter/anthropic/claude-3.5-sonnet
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openrouter/anthropic/claude-3-haiku
- cache_control: true
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: openrouter/anthropic/claude-3.5-sonnet:beta
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  lazy: false
  name: openrouter/anthropic/claude-3.5-sonnet:beta
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openrouter/anthropic/claude-3-haiku:beta
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: vertex_ai/claude-3-5-sonnet@20240620
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  lazy: false
  name: vertex_ai/claude-3-5-sonnet@20240620
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: vertex_ai/claude-3-haiku@20240307
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: vertex_ai/claude-3-5-sonnet-v2@20241022
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  lazy: false
  name: vertex_ai/claude-3-5-sonnet-v2@20241022
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: vertex_ai/claude-3-haiku@20240307
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: vertex_ai/claude-3-opus@20240229
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: vertex_ai/claude-3-haiku@20240307
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: vertex_ai/claude-3-sonnet@20240229
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: vertex_ai/claude-3-haiku@20240307
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: command-r-plus
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: command-r-plus
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: command-r-08-2024
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: command-r-08-2024
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: command-r-plus-08-2024
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: command-r-plus-08-2024
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params: null
  lazy: false
  name: groq/llama3-70b-8192
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: groq/llama3-8b-8192
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params: null
  lazy: false
  name: openrouter/meta-llama/llama-3-70b-instruct
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openrouter/meta-llama/llama-3-70b-instruct
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gemini/gemini-1.5-pro-002
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gemini/gemini-1.5-flash-002
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: false
  edit_format: diff-fenced
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gemini/gemini-1.5-pro
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: false
  edit_format: diff-fenced
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gemini/gemini-1.5-pro-latest
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: false
  edit_format: diff-fenced
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gemini/gemini-1.5-pro-exp-0827
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: gemini/gemini-1.5-flash-exp-0827
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  lazy: false
  name: deepseek/deepseek-chat
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: true
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  lazy: false
  name: deepseek/deepseek-coder
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  lazy: false
  name: deepseek-chat
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: true
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  lazy: false
  name: deepseek-coder
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: null
  editor_model_name: null
  examples_as_sys_msg: true
  extra_params: null
  lazy: false
  name: openrouter/deepseek/deepseek-coder
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: null
  examples_as_sys_msg: false
  extra_params: null
  lazy: true
  name: openrouter/openai/gpt-4o
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openrouter/openai/gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: editor-diff
  editor_model_name: openai/gpt-4o
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: openai/o1-mini
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: openai/gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: editor-diff
  editor_model_name: azure/gpt-4o
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: azure/o1-mini
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: azure/gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: editor-diff
  editor_model_name: gpt-4o
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: o1-mini
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: openai/gpt-4o
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: openai/o1-preview
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: openai/gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: azure/gpt-4o
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: azure/o1-preview
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: azure/gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: architect
  editor_edit_format: editor-diff
  editor_model_name: gpt-4o
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: o1-preview
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: whole
  editor_edit_format: editor-diff
  editor_model_name: openrouter/openai/gpt-4o
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: openrouter/openai/o1-mini
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: openrouter/openai/gpt-4o-mini
- cache_control: false
  caches_by_default: false
  edit_format: diff
  editor_edit_format: editor-diff
  editor_model_name: openrouter/openai/gpt-4o
  examples_as_sys_msg: false
  extra_params: null
  lazy: false
  name: openrouter/openai/o1-preview
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: openrouter/openai/gpt-4o-mini
```
<!--[[[end]]]-->


