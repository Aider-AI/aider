---
parent: Connecting to LLMs
nav_order: 510
---

# LLM API

[LLM API](https://llmapi.ai) is an OpenAI-compatible gateway that provides access to
models from OpenAI, Anthropic, Google, and other providers through a single endpoint.

You'll need an [LLM API key](https://llmapi.ai).

First, install aider:

{% include install.md %}

Then configure your API key:

```bash
export LLMAPI_API_KEY=<key> # Mac/Linux
setx   LLMAPI_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and LLM API on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# GPT-4o via LLM API
aider --model llmapi/gpt-4o

# Claude 3.5 Sonnet via LLM API
aider --model llmapi/claude-3-5-sonnet-20241022

# List all models available from LLM API
aider --list-models llmapi/
```

## Optional config file (`~/.aider.conf.yml`)

```yaml
model: llmapi/gpt-4o
weak-model: llmapi/gpt-4o-mini
```
