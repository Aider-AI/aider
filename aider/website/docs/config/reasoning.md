---
parent: Configuration
nav_order: 110
description: How to configure reasoning model settings from secondary providers.
---

# Reasoning models

Many 
"reasoning" models have restrictions on how they can be used:
they sometimes prohibit streaming, use of temperature and/or the system prompt.
Some also support different levels of "reasoning effort".

Aider is configured to work properly with these models
when served through major provider APIs.

You may need to [configure model settings](/docs/config/adv-model-settings.html)
if you are using them through another provider
and see errors related to temperature or system prompt.

Include settings for your new provider in `.aider.model.setting.yml` file
at the root of your project or in your home directory.

## Reasoning effort

You can use the `--reasoning-effort` switch to control the reasoning effort
of models which support this setting.

## Temperature, streaming and system prompt

You should find one of the existing model setting configuration entries
for the model you are interested in, say o3-mini:

```yaml
- name: o3-mini
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  use_temperature: false             # <---
  editor_model_name: gpt-4o
  editor_edit_format: editor-diff
```

Pay attention to these settings, which must be set to `false`
for certain reasoning models:

- `use_temperature`
- `streaming` 
- `use_system_prompt`

Here's an example of
the settings to use o3-mini via Azure.
Note that aider already has these settings pre-configured, but they
serve as a good example of how to adapt the main model
settings for a different provider.

```yaml
- name: azure/o3-mini
  edit_format: diff
  weak_model_name: azure/gpt-4o-mini
  use_repo_map: true
  use_temperature: false             # <---
  editor_model_name: azure/gpt-4o
  editor_edit_format: editor-diff
```

## Thinking tokens

There is also a `remove_reasoning` setting, which takes the name of a tag.
This is used to remove everything inside that XML tag pair.

For example when using DeepSeek R1 from Fireworks, the reasoning comes back inside
`<think>...</think>` tags, so aider's settings
include `remove_reasoning: think` to remove that part of the response.

Aider will still *display* think reasoning output, it just won't use it
to find file editing instructions, etc.

```yaml
- name: fireworks_ai/accounts/fireworks/models/deepseek-r1
  edit_format: diff
  weak_model_name: fireworks_ai/accounts/fireworks/models/deepseek-v3
  use_repo_map: true
  extra_params:
    max_tokens: 160000
  use_temperature: false
  editor_model_name: fireworks_ai/accounts/fireworks/models/deepseek-v3
  editor_edit_format: editor-diff
  remove_reasoning: think                 # <---
```
