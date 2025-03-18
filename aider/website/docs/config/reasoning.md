---
parent: Configuration
nav_order: 110
description: How to configure reasoning model settings from secondary providers.
---

# Reasoning models

![Thinking demo](/assets/thinking.jpg)

## Reasoning settings

Different models support different reasoning settings. Aider provides several ways to control reasoning behavior:

### Reasoning effort

You can use the `--reasoning-effort` switch to control the reasoning effort
of models which support this setting.
This switch is useful for OpenAI's reasoning models.

### Thinking tokens

You can use the `--thinking-tokens` switch to request
the model use a certain number of thinking tokens.
This switch is useful for Sonnet 3.7.

### Model compatibility warnings

Not all models support these settings. Aider will warn you when you use a setting that may not be supported by your chosen model:

```
Warning: The model claude-3-sonnet@20240229 may not support the 'reasoning_effort' setting.
Sending unsupported parameters can cause API calls to fail. Continue? [y/N]
```

You can disable these warnings with the `--no-check-model-accepts-settings` flag.

Each model has a predefined list of supported settings in its configuration. For example:

- OpenAI reasoning models generally support `reasoning_effort`
- Anthropic reasoning models generally support `thinking_tokens`


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
but it won't be used for file editing instructions, etc.
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

Aider is configured to work properly with these models
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

### Accepting settings configuration

Models define which reasoning settings they accept using the `accepts_settings` property:

```yaml
- name: a-fancy-reasoning-model
  edit_format: diff
  use_repo_map: true
  accepts_settings:                  # <---
    - reasoning_effort               # <---
```

This tells Aider that the model accepts the `reasoning_effort` setting but not `thinking_tokens`.
So you would get a warning if you try to use `--thinking-tokens` with this model.
