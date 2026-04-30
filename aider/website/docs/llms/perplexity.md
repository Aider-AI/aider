---
parent: Connecting to LLMs
nav_order: 510
---

# Perplexity

Aider can connect to [Perplexity's Sonar models](https://docs.perplexity.ai/models/model-cards)
through Perplexity's OpenAI-compatible Agent API.
You'll need a [Perplexity API key](https://www.perplexity.ai/settings/api).

First, install aider:

{% include install.md %}

Then configure your API keys:

```
export PERPLEXITY_API_KEY=<key> # Mac/Linux
setx   PERPLEXITY_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and Perplexity on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use Perplexity's default Sonar Pro model
aider --model perplexity/sonar-pro

# Or any other Perplexity model
aider --model perplexity/sonar
aider --model perplexity/sonar-reasoning
aider --model perplexity/sonar-reasoning-pro
aider --model perplexity/sonar-deep-research

# List models available from Perplexity
aider --list-models perplexity/
```

Perplexity exposes an OpenAI-compatible Agent API at
`https://api.perplexity.ai`, so requests go through aider's standard
OpenAI-compatible client (via LiteLLM).

## Available models

- `perplexity/sonar` — fast, lightweight Sonar model
- `perplexity/sonar-pro` — flagship Sonar model (default)
- `perplexity/sonar-reasoning` — Sonar with chain-of-thought reasoning
- `perplexity/sonar-reasoning-pro` — high-capacity reasoning model
- `perplexity/sonar-deep-research` — long-form research model

See [Perplexity's documentation](https://docs.perplexity.ai) for the latest
model list, pricing, and feature details.
