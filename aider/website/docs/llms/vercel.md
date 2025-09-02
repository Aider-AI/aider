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

## Helpful Links

- [Team dashboard](https://vercel.com/d?to=%2F%5Bteam%5D%2F%7E%2Fai)
- [Models catalog](https://vercel.com/ai-gateway/models)
- [Docs](https://vercel.com/docs/ai-gateway)