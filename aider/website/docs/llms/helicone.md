---
parent: Connecting to LLMs
nav_order: 505
---

# Helicone

Aider can connect to models via the Helicone gateway and public model registry.
You'll need a `HELICONE_API_KEY`.

First, install aider:

{% include install.md %}

Then configure your API key:

```
export HELICONE_API_KEY=<key> # Mac/Linux
setx   HELICONE_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and Helicone on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use any model id from the Helicone registry
aider --model helicone/<model-id>

# Example
aider --model helicone/gpt-4o

# List models available from Helicone
aider --list-models helicone/
```

Notes
- Helicone acts as a gateway; aider routes requests through Helicone automatically when you use `helicone/...` models.
- Aider requires only `HELICONE_API_KEY` to use Helicone models.
- Use the model id directly after the `helicone/` prefix (for example `helicone/gpt-4o`).

See [Advanced model settings](/docs/config/adv-model-settings.html#model-settings) for details on per‑model configuration.
