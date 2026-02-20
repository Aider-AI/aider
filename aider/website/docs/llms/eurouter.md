---
parent: Connecting to LLMs
nav_order: 500
---

# EUrouter

Aider can connect to [models provided by EUrouter](https://eurouter.ai):
You'll need an [EUrouter API key](https://eurouter.ai).

First, install aider:

{% include install.md %}

Then configure your API key:

```
export EUROUTER_API_KEY=<key> # Mac/Linux
setx   EUROUTER_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and EUrouter on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use any EUrouter model
aider --model eurouter/<model>

# List models available from EUrouter
aider --list-models eurouter/
```

For example:

```bash
aider --model eurouter/claude-opus-4-6
aider --model eurouter/deepseek-r1
aider --model eurouter/mistral-large-3
```

## Model variants

EUrouter supports model variants that control provider selection.
Append a variant suffix to any model name:

```bash
aider --model eurouter/claude-opus-4-6:floor  # Cheapest provider
aider --model eurouter/claude-opus-4-6:nitro  # Fastest provider
aider --model eurouter/deepseek-r1:free       # Free providers only
```

## Controlling provider routing

EUrouter routes each request to an optimal provider based on health, price,
and availability. You can control which providers are used for your requests
by configuring "provider routing" in a `.aider.model.settings.yml` file.

Place that file in your home directory or the root of your git project, with
entries like this:

```yaml
- name: eurouter/claude-opus-4-6
  extra_params:
    extra_body:
      provider:
        # Only use these providers, in this order
        order: ["anthropic", "scaleway"]
        # Don't fall back to other providers
        allow_fallbacks: false
        # Skip providers that may train on inputs
        data_collection: "deny"
        # Only use providers supporting all parameters
        require_parameters: true
        # Only process in EU/EEA regions
        data_residency: "eu"
        # Only use EU-headquartered providers (Scaleway, OVHcloud, IONOS, GreenPT)
        eu_owned: true
```

EUrouter routes through EU infrastructure by default. The `data_residency`
and `eu_owned` options provide stricter control for compliance requirements.

See [EUrouter's provider routing docs](https://eurouter.ai/docs/provider-routing) for full details on these settings.

See [Advanced model settings](https://aider.chat/docs/config/adv-model-settings.html#model-settings)
for more details about model settings files.

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.
