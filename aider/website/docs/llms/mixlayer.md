---
parent: Connecting to LLMs
nav_order: 515
---

# Mixlayer

Aider can connect to [Mixlayer](https://mixlayer.com).
Mixlayer serves open-source models behind an OpenAI-compatible API.
You'll need a [Mixlayer API key](https://console.mixlayer.com/app/api-keys).

Aider connects to providers through [LiteLLM](https://docs.litellm.ai/docs/providers).
LiteLLM has no `mixlayer/` provider, so use the OpenAI-compatible client and set the base URL.
Context windows and token prices belong in
[LiteLLM's model metadata](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json).
Until that file includes these models, aider will warn that the context window and costs are unknown.
That warning is safe to ignore.
See [model warnings](warnings.html).

First, install aider:

{% include install.md %}

Then configure your API key and endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=https://mixlayer.ai/v1
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE https://mixlayer.ai/v1
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Mixlayer's own docs call the key `MIXLAYER_API_KEY`.
This path reads `OPENAI_API_KEY`, which is what LiteLLM's OpenAI client expects.
`https://mixlayer.ai/v1` is the nearest-edge base URL from the [Mixlayer quickstart](https://docs.mixlayer.com/quickstart.md).

Start working with aider and Mixlayer on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Prefix the model name with openai/
aider --model openai/qwen/qwen3.5-9b

# Free model
aider --model openai/qwen/qwen3.5-4b-free
```

Model IDs currently served at that endpoint:

- `z-ai/glm-5.3`
- `qwen/qwen3.8-27b`
- `qwen/qwen3.6-35b-a3b`
- `deepseek/deepseek-v4.1-flash`
- `qwen/qwen3.5-9b`
- `qwen/qwen3.5-4b-free`

See the [Mixlayer docs](https://docs.mixlayer.com) if the list has changed.

These models think by default.
`z-ai/glm-5.3` always reasons and rejects a `reasoning_effort` of `none`.
The others accept `none` to turn thinking off.
Aider does not send `reasoning_effort` unless you configure it yourself.
