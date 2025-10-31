---
parent: Connecting to LLMs
nav_order: 400
---

# xAI

You'll need a [xAI API key](https://console.x.ai.).

First, install aider:

{% include install.md %}

Then configure your API keys:

```bash
export XAI_API_KEY=<key> # Mac/Linux
setx   XAI_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and xAI on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Grok 3
aider --model xai/grok-3-beta

# Grok 3 fast (faster, more expensive)
aider --model xai/grok-3-fast-beta

# Grok 3 Mini
aider --model xai/grok-3-mini-beta

# Grok 3 Mini fast (faster, more expensive)
aider --model xai/grok-3-mini-fast-beta

# List models available from xAI
aider --list-models xai/
```

The Grok 3 Mini models support the `--reasoning-effort` flag.
See the [reasoning settings documentation](../config/reasoning.md) for details.
Example:

```bash
aider --model xai/grok-3-mini-beta --reasoning-effort high
```




