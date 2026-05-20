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

## Tuning Engines

Tuning Engines exposes an OpenAI compatible inference endpoint, so it works with
aider through the same configuration:

```
# Mac/Linux:
export OPENAI_API_BASE=https://api.tuningengines.com/v1
export OPENAI_API_KEY=sk-te-...

# Windows:
setx OPENAI_API_BASE https://api.tuningengines.com/v1
setx OPENAI_API_KEY sk-te-...
# ... restart shell after setx commands
```

Then run aider with a model alias that is enabled for your Tuning Engines key:

```bash
aider --model openai/<your-model-alias>
```

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.
