---
parent: Connecting to LLMs
nav_order: 450
---

# Avian

Aider can connect to [Avian's](https://avian.io) OpenAI-compatible API.
Avian provides access to frontier open-source models at competitive prices.

You'll need an [Avian API key](https://avian.io).

First, install aider:

{% include install.md %}

Then configure your API key:

```bash
export AVIAN_API_KEY=<key> # Mac/Linux
setx   AVIAN_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and Avian on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# DeepSeek V3.2 — 164K context, best value
aider --model avian/deepseek-v3.2

# Kimi K2.5 by Moonshot AI
aider --model avian/kimi-k2.5

# GLM-5 by Zhipu AI
aider --model avian/glm-5

# MiniMax M2.5 — 1M context window
aider --model avian/minimax-m2.5

# List models available from Avian
aider --list-models avian/
```
