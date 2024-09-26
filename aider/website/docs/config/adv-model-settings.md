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
[models.py](https://github.com/paul-gauthier/aider/blob/main/aider/models.py)
file for more details about all of the model setting that aider supports.

<!--[[[cog
from aider.models import get_model_settings_as_yaml
cog.out("```yaml\n")
cog.out(get_model_settings_as_yaml())
cog.out("```\n")
]]]-->
```yaml
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gpt-3.5-turbo
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gpt-3.5-turbo-0125
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gpt-3.5-turbo-1106
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gpt-3.5-turbo-0613
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gpt-3.5-turbo-16k-0613
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: udiff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: gpt-4-turbo-2024-04-09
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: udiff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: gpt-4-turbo
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: openai/gpt-4o
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: openai/gpt-4o-2024-08-06
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: gpt-4o-2024-08-06
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: gpt-4o
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: gpt-4o-mini
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: openai/gpt-4o-mini
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openai/gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: udiff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: gpt-4-0125-preview
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: udiff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: gpt-4-1106-preview
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gpt-4-vision-preview
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gpt-4-0314
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gpt-4-0613
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gpt-4-32k-0613
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: claude-3-opus-20240229
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: openrouter/anthropic/claude-3-opus
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openrouter/anthropic/claude-3-haiku
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: claude-3-sonnet-20240229
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- accepts_images: true
  cache_control: true
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers:
    anthropic-beta: prompt-caching-2024-07-31
  junior_edit_format: junior-diff
  junior_model_name: claude-3-5-sonnet-20240620
  lazy: false
  max_tokens: 8192
  name: claude-3-5-sonnet-20240620
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- accepts_images: false
  cache_control: true
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers:
    anthropic-beta: prompt-caching-2024-07-31
  junior_edit_format: junior-diff
  junior_model_name: anthropic/claude-3-5-sonnet-20240620
  lazy: false
  max_tokens: 8192
  name: anthropic/claude-3-5-sonnet-20240620
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- accepts_images: false
  cache_control: true
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: true
  extra_body: null
  extra_headers:
    anthropic-beta: prompt-caching-2024-07-31
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: anthropic/claude-3-haiku-20240307
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: anthropic/claude-3-haiku-20240307
- accepts_images: false
  cache_control: true
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: true
  extra_body: null
  extra_headers:
    anthropic-beta: prompt-caching-2024-07-31
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: claude-3-haiku-20240307
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: claude-3-haiku-20240307
- accepts_images: true
  cache_control: true
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: openrouter/anthropic/claude-3.5-sonnet
  lazy: false
  max_tokens: 8192
  name: openrouter/anthropic/claude-3.5-sonnet
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openrouter/anthropic/claude-3-haiku-20240307
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: vertex_ai/claude-3-5-sonnet@20240620
  lazy: false
  max_tokens: 8192
  name: vertex_ai/claude-3-5-sonnet@20240620
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: vertex_ai/claude-3-haiku@20240307
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: vertex_ai/claude-3-opus@20240229
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: vertex_ai/claude-3-haiku@20240307
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: vertex_ai/claude-3-sonnet@20240229
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: vertex_ai/claude-3-haiku@20240307
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: command-r-plus
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: command-r-plus
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: command-r-08-2024
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: command-r-08-2024
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: command-r-plus-08-2024
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: command-r-plus-08-2024
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: groq/llama3-70b-8192
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: groq/llama3-8b-8192
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: openrouter/meta-llama/llama-3-70b-instruct
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openrouter/meta-llama/llama-3-70b-instruct
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gemini/gemini-1.5-pro-002
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gemini/gemini-1.5-flash-002
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff-fenced
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gemini/gemini-1.5-pro
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff-fenced
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gemini/gemini-1.5-pro-latest
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff-fenced
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gemini/gemini-1.5-pro-exp-0827
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: gemini/gemini-1.5-flash-exp-0827
  reminder: user
  send_undo_reply: false
  streaming: true
  use_repo_map: false
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: 8192
  name: deepseek/deepseek-chat
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: true
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: 8192
  name: deepseek/deepseek-coder
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: 8192
  name: deepseek-chat
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: true
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: 8192
  name: deepseek-coder
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: true
  extra_body: null
  extra_headers: null
  junior_edit_format: null
  junior_model_name: null
  lazy: false
  max_tokens: null
  name: openrouter/deepseek/deepseek-coder
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: null
- accepts_images: true
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: null
  lazy: true
  max_tokens: null
  name: openrouter/openai/gpt-4o
  reminder: sys
  send_undo_reply: false
  streaming: true
  use_repo_map: true
  use_system_prompt: true
  use_temperature: true
  weak_model_name: openrouter/openai/gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: openai/gpt-4o
  lazy: false
  max_tokens: null
  name: openai/o1-mini
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: openai/gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: gpt-4o
  lazy: false
  max_tokens: null
  name: o1-mini
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: openai/gpt-4o
  lazy: false
  max_tokens: null
  name: openai/o1-preview
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: openai/gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: senior
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: gpt-4o
  lazy: false
  max_tokens: null
  name: o1-preview
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: whole
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: openrouter/openai/gpt-4o
  lazy: false
  max_tokens: null
  name: openrouter/openai/o1-mini
  reminder: user
  send_undo_reply: false
  streaming: false
  use_repo_map: true
  use_system_prompt: false
  use_temperature: false
  weak_model_name: openrouter/openai/gpt-4o-mini
- accepts_images: false
  cache_control: false
  caches_by_default: false
  edit_format: diff
  examples_as_sys_msg: false
  extra_body: null
  extra_headers: null
  junior_edit_format: junior-diff
  junior_model_name: openrouter/openai/gpt-4o
  lazy: false
  max_tokens: null
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


