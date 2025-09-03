---
parent: Connecting to LLMs
nav_order: 550
---

# Vercel AI Gateway

Aider can connect to [models provided by the Vercel AI Gateway](https://vercel.com/ai-gateway).
You'll need a [Vercel AI Gateway API key](https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai%2Fapi-keys&title=AI+Gateway+API+Key).

First, install aider:

{% include install.md %}

Then configure your API key:

```
export VERCEL_AI_GATEWAY_API_KEY=<key> # Mac/Linux
setx   VERCEL_AI_GATEWAY_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and Vercel AI Gateway on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use a specific model through Vercel AI Gateway
aider --model vercel_ai_gateway/<provideer>/<model>

# List models available from Vercel AI Gateway
aider --list-models vercel_ai_gateway/
```

## Controlling provider selection

The Vercel AI Gateway often has multiple providers serving each model.
You can control which providers are used for your requests by configuring "provider options" in a `.aider.model.settings.yml` file.

Place that file in your home directory or the root of your git project, with
entries like this:

```yaml
- name: vercel_ai_gateway/anthropic/claude-sonnet-4
  extra_params:
    providerOptions:
      gateway:
        # Filter to these providers only
        only: ['bedrock', 'anthropic', 'vertex']
        # Use providers in this order of preference
        order: ['bedrock', 'vertex', 'anthropic']
```

See [Vercel AI Gateway provider options docs](https://vercel.com/docs/ai-gateway/provider-options) for full details on these settings.

## Helpful Links

- [Team dashboard](https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai)
- [Models catalog](https://vercel.com/ai-gateway/models)
- [Docs](https://vercel.com/docs/ai-gateway)