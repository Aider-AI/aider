---
parent: Connecting to LLMs
nav_order: 500
---

# OpenRouter

Aider can connect to [models provided by OpenRouter](https://openrouter.ai/models?o=top-weekly):
You'll need an [OpenRouter API key](https://openrouter.ai/keys).

```
python -m pip install -U aider-chat

export OPENROUTER_API_KEY=<key> # Mac/Linux
setx   OPENROUTER_API_KEY <key> # Windows, restart shell after setx

# Or any other open router model
aider --model openrouter/<provider>/<model>

# List models available from OpenRouter
aider --list-models openrouter/
```

In particular, many aider users access Sonnet via OpenRouter:

```
python -m pip install -U aider-chat

export OPENROUTER_API_KEY=<key> # Mac/Linux
setx   OPENROUTER_API_KEY <key> # Windows, restart shell after setx

aider --model openrouter/anthropic/claude-3.7-sonnet
```


{: .tip }
If you get errors, check your
[OpenRouter privacy settings](https://openrouter.ai/settings/privacy).
Be sure to "enable providers that may train on inputs"
to allow use of all models.

## Controlling provider selection

OpenRouter often has multiple providers serving each model.
You can control which OpenRouter providers are used for your requests in two ways:

1. By "ignoring" certain providers in your
[OpenRouter account settings](https://openrouter.ai/settings/preferences).
This disables those named providers across all the models that you access via OpenRouter.

2. By configuring "provider routing" in a `.aider.model.settings.yml` file.

Place that file in your home directory or the root of your git project, with
entries like this:

```yaml
- name: openrouter/anthropic/claude-3.7-sonnet
  extra_params:
    extra_body:
      provider:
        # Only use these providers, in this order
        order: ["Anthropic", "Together"]
        # Don't fall back to other providers
        allow_fallbacks: false
        # Skip providers that may train on inputs
        data_collection: "deny"
        # Only use providers supporting all parameters
        require_parameters: true
```

See [OpenRouter's provider routing docs](https://openrouter.ai/docs/provider-routing) for full details on these settings.

See [Advanced model settings](https://aider.chat/docs/config/adv-model-settings.html#model-settings)
for more details about model settings files. 



