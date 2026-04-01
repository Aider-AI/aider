---
parent: Connecting to LLMs
nav_order: 500
---

# EUrouter

Aider can connect to models provided by [EUrouter](https://eurouter.ai),
the European AI gateway that gives access to all European-hosted AI models.
You'll need an [EUrouter API key](https://eurouter.ai).

EUrouter provides an OpenAI-compatible API, so it works with aider
via the `openai/` provider prefix.

First, install aider:

{% include install.md %}

Then configure your API key and base URL:

```
export OPENAI_API_BASE=https://api.eurouter.ai/api/v1 # Mac/Linux
export OPENAI_API_KEY=eur_...                          # Your EUrouter key

setx OPENAI_API_BASE https://api.eurouter.ai/api/v1   # Windows
setx OPENAI_API_KEY eur_...                            # restart shell after setx
```

Start working with aider and EUrouter on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use DeepSeek R1 via EUrouter
aider --model openai/deepseek-r1

# Use Mistral Large 3 via EUrouter
aider --model openai/mistral-large-3

# List available models
aider --list-models openai/
```

{: .tip }
EUrouter routes requests to EU-resident infrastructure by default.
You can configure data residency, provider preferences, and fallback
behavior in your [EUrouter dashboard](https://eurouter.ai).
