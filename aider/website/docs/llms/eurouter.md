---
parent: Connecting to LLMs
nav_order: 500
---

# EUrouter

EUrouter is a GDPR-compliant AI model router for EU customers.
It's a drop-in replacement for OpenRouter's API, routing requests
to providers with EU data residency.

EUrouter works with aider via its OpenAI-compatible API endpoint.

First, install aider:

{% include install.md %}

Next, configure your API key and endpoint:

```
export OPENAI_API_BASE=https://api.eurouter.eu/v1  # Mac/Linux
export OPENAI_API_KEY=<key>
setx   OPENAI_API_BASE https://api.eurouter.eu/v1  # Windows, restart shell after setx
setx   OPENAI_API_KEY <key>
```

Start working with aider and EUrouter on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

aider --model openai/anthropic/claude-sonnet-4-20250514
```

You can find available models and get an API key at
[eurouter.eu](https://eurouter.eu).
