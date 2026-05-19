---
parent: Connecting to LLMs
nav_order: 510
---

# QuickSilver Pro

Aider can connect to models served by
[QuickSilver Pro](https://quicksilverpro.io), an OpenAI-compatible gateway
for 12 frontier open-source models: DeepSeek V4 Flash / V4 Pro / V3 / R1,
Qwen 3.5 / 3.6, Kimi K2.6, and the Gemini 2.5 / 3 family.
QuickSilver Pro is priced ~20% below OpenRouter on the shared model set
and returns standard `usage.cost` on every response, so aider's
session-cost display works without configuration.

You'll need a [QuickSilver Pro API key](https://quicksilverpro.io/dashboard/).

First, install aider:

{% include install.md %}

Then configure your API key. QuickSilver Pro speaks the OpenAI API, so
the standard `OPENAI_API_BASE` and `OPENAI_API_KEY` variables are all you
need:

```
export OPENAI_API_BASE=https://api.quicksilverpro.io/v1
export OPENAI_API_KEY=<key>     # Mac/Linux
setx   OPENAI_API_BASE https://api.quicksilverpro.io/v1
setx   OPENAI_API_KEY <key>     # Windows, restart shell after setx
```

Then start working with aider against any of QuickSilver Pro's models —
prefix the model name with `openai/` so litellm routes through the OpenAI
client:

```bash
# Change directory into your codebase
cd /to/your/project

# DeepSeek V4 Pro — strong on multi-file refactors
aider --model openai/deepseek-v4-pro

# DeepSeek V4 Flash — cheap chat with 1M context
aider --model openai/deepseek-v4-flash

# Kimi K2.6 — Opus-class agentic / planning
aider --model openai/kimi-k2.6
```

The full model list and per-model pricing is at
[quicksilverpro.io/docs/models](https://quicksilverpro.io/docs/models/);
integration tips for other tools are at
[quicksilverpro.io/docs/integrations](https://quicksilverpro.io/docs/integrations/).
