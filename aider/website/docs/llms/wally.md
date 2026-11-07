---
parent: Connecting to LLMs
nav_order: 500
---

# Wally

Aider can connect to [Wally](https://www.runwally.com), an OpenAI compatible API
by RunAnywhere for open-weight models like DeepSeek, GLM, Kimi and MiniMax.
You'll need a [Wally API key](https://console.runanywhere.ai).

First, install aider:

{% include install.md %}

Then configure your API key and endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=https://inference.runanywhere.ai/v1
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE https://inference.runanywhere.ai/v1
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Start working with aider and Wally on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Prefix the model name with openai/
aider --model openai/deepseek-v4.1-flash

# Use a smaller model for commit messages and chat summaries
aider --model openai/deepseek-v4.1-flash --weak-model openai/glm-5.3-flash
```

List the available model ids (no API key needed):

```bash
curl -s https://inference.runanywhere.ai/v1/models | jq -r '.data[].id'
```

Prices are on the [Wally pricing page](https://www.runwally.com/pricing).

## Context window sizes

Aider doesn't know these models, so it will show
[model warnings](warnings.html) about unknown context window sizes and costs.
You can ignore them, or register the models in a `.aider.model.metadata.json`
file, using the limits from the models endpoint above:

```
{
    "openai/deepseek-v4.1-flash": {
        "max_input_tokens": 1048576,
        "max_output_tokens": 65536,
        "litellm_provider": "openai",
        "mode": "chat"
    }
}
```

See [Advanced model settings](/docs/config/adv-model-settings.html#context-window-size-and-token-costs)
for where to put this file.
