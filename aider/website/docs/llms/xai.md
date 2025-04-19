---
parent: Connecting to LLMs
nav_order: 400
---

# xAI

You'll need a [xAI API key](https://console.x.ai.).

To use xAI:

```bash
python -m pip install aider-install
aider-install

export XAI_API_KEY=<key> # Mac/Linux
setx   XAI_API_KEY <key> # Windows, restart shell after setx

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




