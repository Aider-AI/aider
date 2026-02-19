---
parent: Connecting to LLMs
nav_order: 500
---

# EUrouter

Aider can connect to the 100+ models available on [EUrouter](https://eurouter.ai),
a European AI routing API with GDPR-compliant EU data residency by default.

You'll need an [EUrouter API key](https://eurouter.ai).

First, install aider:

{% include install.md %}

Then configure your API keys:

```
# Mac/Linux:
export OPENAI_API_BASE=https://api.eurouter.ai/api/v1
export EUROUTER_API_KEY=eur-...

# Windows:
setx OPENAI_API_BASE https://api.eurouter.ai/api/v1
setx EUROUTER_API_KEY eur-...
# ... restart shell after setx commands
```

Start working with aider and EUrouter on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use any model available on EUrouter
aider --model openai/claude-opus-4-6
aider --model openai/mistral-large-3
aider --model openai/deepseek-r1
aider --model openai/gpt-5-mini
aider --model openai/gpt-oss-120b
aider --model openai/green-r
aider --model openai/kimi-k2.5
```

Since EUrouter uses the OpenAI-compatible API format, it works with aider's
existing OpenAI provider by setting the base URL. All requests are routed
through EU infrastructure.

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.
