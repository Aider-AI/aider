---
parent: Connecting to LLMs
nav_order: 500
---

# OpenCheap

[OpenCheap](https://opencheap.si) is an OpenAI compatible API with one key for
open and closed models. Aider connects to it through its
[OpenAI compatible API](openai-compat.html) support.
Create an API key at [app.opencheap.si](https://app.opencheap.si).
Model ids and prices are listed at [opencheap.si/pricing](https://opencheap.si/pricing).

First, install aider:

{% include install.md %}

Then configure your API key and the OpenCheap endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=https://api.opencheap.si/v1
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE https://api.opencheap.si/v1
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Start working with aider and OpenCheap on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Prefix the OpenCheap model id with openai/
aider --model openai/qwen3-coder
```

The model id is the name without a vendor prefix, as returned by
`GET https://api.opencheap.si/v1/models`.

## Model warnings

Aider doesn't know the context window of these models, so it prints a
[model warning](warnings.html) and uses default limits.
To remove the warning, describe the model in a
`.aider.model.metadata.json` file in your home directory or the root of your
project, using the `context_length` from `/v1/models`:

```json
{
  "openai/qwen3-coder": {
    "max_input_tokens": 262144,
    "litellm_provider": "openai",
    "mode": "chat"
  }
}
```

See [Advanced model settings](https://aider.chat/docs/config/adv-model-settings.html#model-settings)
for more details about model settings files.
