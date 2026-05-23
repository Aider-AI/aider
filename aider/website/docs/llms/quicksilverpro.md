---
parent: Connecting to LLMs
nav_order: 450
---

# QuickSilver Pro

Aider can connect to open-source models (DeepSeek V3, DeepSeek R1, Qwen3.5-35B-A3B)
through [QuickSilver Pro](https://quicksilverpro.io)'s OpenAI-compatible API.

First, install aider:

{% include install.md %}

Get a QuickSilver Pro API key at [quicksilverpro.io/dashboard](https://quicksilverpro.io/dashboard),
then point aider at the endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=https://api.quicksilverpro.io/v1
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE https://api.quicksilverpro.io/v1
setx OPENAI_API_KEY <key>
```

Then run aider with one of the supported models:

```bash
aider --model openai/deepseek-v3     # general coding, JSON, tool calls
aider --model openai/deepseek-r1     # reasoning-heavy tasks
aider --model openai/qwen3.5-35b     # 262K context, long-document RAG
```

The `openai/` prefix tells aider to use the OpenAI-compatible client; the
segment after the slash is the QuickSilver Pro model ID.
