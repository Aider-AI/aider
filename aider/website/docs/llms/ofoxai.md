---
parent: Connecting to LLMs
nav_order: 510
---

# OfoxAI

Aider can connect to [models provided by OfoxAI](https://ofox.ai),
a unified LLM API gateway that exposes 100+ models — including
GPT, Claude, Gemini, DeepSeek, Qwen, Llama, and Mistral — through
a single OpenAI-compatible endpoint.
You'll need an [OfoxAI API key](https://app.ofox.ai/auth).

First, install aider:

{% include install.md %}

Then configure your API key and endpoint. OfoxAI is OpenAI-compatible,
so set `OPENAI_API_BASE` to OfoxAI's `/v1` endpoint and `OPENAI_API_KEY`
to your OfoxAI key:

```
# Mac/Linux:
export OPENAI_API_BASE=https://api.ofox.ai/v1
export OPENAI_API_KEY=<your-ofoxai-key>

# Windows:
setx OPENAI_API_BASE https://api.ofox.ai/v1
setx OPENAI_API_KEY <your-ofoxai-key>
# ... restart shell after setx commands
```

Start working with aider on your codebase. Prefix the model name
with `openai/` so litellm uses the OpenAI-compatible adapter:

```bash
# Change directory into your codebase
cd /to/your/project

# Pick any model available in your OfoxAI account
aider --model openai/gpt-4o
aider --model openai/claude-sonnet-4-20250514
aider --model openai/gemini-2.5-pro
aider --model openai/deepseek-v3
```

The full list of model IDs is shown in the
[OfoxAI dashboard](https://app.ofox.ai)
and at [docs.ofox.ai](https://docs.ofox.ai).

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.

## Native Anthropic and Gemini protocols

OfoxAI also exposes native Anthropic and Gemini protocol endpoints
that work with aider's built-in `anthropic/` and `gemini/` model
prefixes. Most users do not need this, but it can be useful when
you want full feature parity with the upstream protocol (for
example, prompt caching headers).

```bash
# Anthropic protocol
export ANTHROPIC_API_BASE=https://api.ofox.ai/anthropic
export ANTHROPIC_API_KEY=<your-ofoxai-key>
aider --model anthropic/claude-sonnet-4-20250514

# Gemini protocol
export GEMINI_API_BASE=https://api.ofox.ai/gemini
export GEMINI_API_KEY=<your-ofoxai-key>
aider --model gemini/gemini-2.5-pro
```

## Tips

- OfoxAI offers a free tier for evaluation and pay-per-token usage thereafter.
- All endpoints are routed for global access and optimized for users in
  mainland China via Hong Kong express routing.
- Because OfoxAI passes the OpenAI Chat Completions API through, all of
  aider's existing features — streaming, tool use on supported models,
  vision input — work without extra configuration.
