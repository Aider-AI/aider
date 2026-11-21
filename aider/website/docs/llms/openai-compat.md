---
parent: Connecting to LLMs
nav_order: 500
---

# OpenAI compatible APIs

Aider can connect to any LLM which is accessible via an OpenAI compatible API endpoint.

First, install aider:

{% include install.md %}

Then configure your API key and endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=<endpoint>
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE <endpoint>
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Start working with aider and your OpenAI compatible API on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Prefix the model name with openai/
aider --model openai/<model-name>
```

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.

## Example: Kimi K3.1 Pro via Wallaby

Wallaby serves Moonshot AI's Kimi K3.1 Pro through an OpenAI-compatible endpoint. Create a key at [wallabytoken.com](https://wallabytoken.com) ($0.50 trial credit, no card required), then configure and run:

```bash
# Mac/Linux:
export OPENAI_API_BASE=https://api.wallabytoken.com/v1
export OPENAI_API_KEY=<your Wallaby key>

# Windows:
setx OPENAI_API_BASE https://api.wallabytoken.com/v1
setx OPENAI_API_KEY <your Wallaby key>
# ... restart shell after setx commands

# Prefix the model name with openai/
aider --model openai/kimi-k3.1-pro
```

Notes:

- `kimi-k3.1-pro-highspeed` and `kimi-k3` are available on the same endpoint with the same key.
- Pricing: $1.80 / 1M input ($0.18 cached), $9.00 / 1M output. Machine-readable rate card: [pricing.json](https://wallabytoken.com/pricing.json).
- Public status page: [status.wallabytoken.com](https://status.wallabytoken.com).
