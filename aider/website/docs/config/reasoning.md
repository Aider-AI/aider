---
parent: Configuration
nav_order: 110
description: How to configure reasoning model settings from secondary providers.
---

# Reasoning models

![Thinking demo](/assets/thinking.jpg)

## Basic usage

Aider is configured to work with most popular reasoning models out of the box. 
You can use them like this:

```bash
# Sonnet uses a thinking token budget
aider --model sonnet --thinking-tokens 8k

# o3-mini uses low/medium/high reasoning effort
aider --model o3-mini --reasoning-effort high

# R1 doesn't have configurable thinking/reasoning
aider --model r1
```

Inside the aider chat, you can use `/thinking-tokens 4k` or `/reasoning-effort low` to change
the amount of reasoning.

The rest of this document describes more advanced details which are mainly needed
if you're configuring aider to work with a lesser known reasoning model or one served
via an unusual provider.

## Reasoning settings

Different models support different reasoning settings. Aider provides several ways to control reasoning behavior:

### Reasoning effort

You can use the `--reasoning-effort` switch to control the reasoning effort
of models which support this setting.
This switch is useful for OpenAI's reasoning models, which accept "low", "medium" and "high".

### Thinking tokens

You can use the `--thinking-tokens` switch to request
the model use a certain number of thinking tokens.
This switch is useful for Sonnet 3.7.
You can specify the token budget like "1024", "1k", "8k" or "0.01M".

### Model compatibility and settings

Not all models support these two settings. Aider uses the 
[model's metadata](/docs/config/adv-model-settings.html)
to determine which settings each model accepts:

```yaml
- name: o3-mini
  ...
  accepts_settings: ["reasoning_effort"]
```

If you try to use a setting that a model doesn't explicitly support, Aider will warn you:

```
Warning: o3-mini does not support 'thinking_tokens', ignoring.
Use --no-check-model-accepts-settings to force the 'thinking_tokens' setting.
```

The warning informs you that:
1. The setting won't be applied because the model doesn't list it in `accepts_settings`
2. You can use `--no-check-model-accepts-settings` to force the setting anyway

This functionality helps prevent API errors while still allowing you to experiment with settings when needed.

Each model has a predefined list of supported settings in its configuration. For example:

- OpenAI reasoning models generally support `reasoning_effort`
- Anthropic reasoning models generally support `thinking_tokens`


### How `accepts_settings` works

Models define which reasoning settings they accept using the `accepts_settings` property:

```yaml
- name: a-fancy-reasoning-model
  edit_format: diff
  use_repo_map: true
  accepts_settings:                  # <---
    - reasoning_effort               # <---
```

This configuration:
1. Tells Aider that the model accepts the `reasoning_effort` setting
2. Indicates the model does NOT accept `thinking_tokens` (since it's not listed)
3. Causes Aider to ignore any `--thinking-tokens` value passed for this model
4. Generates a warning if you try to use `--thinking-tokens` with this model

You can override this behavior with `--no-check-model-accepts-settings`, which will:
1. Force Aider to apply all settings passed via command line
2. Skip all compatibility checks
3. Potentially cause API errors if the model truly doesn't support the setting

This is useful when testing new models or using models through custom API providers.


## Thinking tokens in XML tags

There is also a `reasoning_tag` setting, which takes the name of an XML tag
that the model uses to wrap its reasoning/thinking output.

For example when using DeepSeek R1 from Fireworks, the reasoning comes back inside
`<think>...</think>` tags, so aider's settings
include `reasoning_tag: think`.

```
<think>
The user wants me to greet them!
</think>

Hello!
```

Aider will display the thinking/reasoning output, 
but it won't be used for file editing instructions, added to the chat history, etc.
Aider will rely on the non-thinking output for instructions on how to make code changes, etc.

### Model-specific reasoning tags

Different models use different XML tags for their reasoning:
When using custom or self-hosted models, you may need to specify the appropriate reasoning tag in your configuration.

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
  reasoning_tag: think                 # <---
```

## Reasoning model limitations

Many "reasoning" models have restrictions on how they can be used:
they sometimes prohibit streaming, use of temperature and/or the system prompt.
Aider is configured to work properly with popular models
when served through major provider APIs.

If you're using a model through a different provider (like Azure or custom deployment),
you may need to [configure model settings](/docs/config/adv-model-settings.html)
if you see errors related to temperature or system prompt.

Include settings for your new provider in `.aider.model.settings.yml` file
at the root of your project or in your home directory.

### Temperature, streaming and system prompt

Reasoning models often have specific requirements for these settings:

| Setting | Description | Common Restrictions |
|---------|-------------|---------------------|
| `use_temperature` | Whether to use temperature sampling | Many reasoning models require this set to `false` |
| `streaming` | Whether to stream responses | Some reasoning models don't support streaming |
| `use_system_prompt` | Whether to use system prompt | Some reasoning models don't support system prompts |

It may be helpful to find one of the 
[existing model setting configuration entries](https://github.com/Aider-AI/aider/blob/main/aider/resources/model-settings.yml)
for the model you are interested in, say o3-mini:

```yaml
- name: o3-mini
  edit_format: diff
  weak_model_name: gpt-4o-mini
  use_repo_map: true
  use_temperature: false             # <---
  editor_model_name: gpt-4o
  editor_edit_format: editor-diff
  accepts_settings: ["reasoning_effort"]
```

Pay attention to these settings, which must be set to `false`
for certain reasoning models:

- `use_temperature`
- `streaming` 
- `use_system_prompt`

### Custom provider example

Here's an example of the settings to use o3-mini via Azure.
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
  accepts_settings: ["reasoning_effort"]
```
