---
parent: Connecting to LLMs
nav_order: 500
---

# Nodecode

Aider can connect to the [Nodecode](https://nodecode.ai) API, which is OpenAI compatible.
Nodecode serves Cyber v1 (`nodecode-cyber-v1`), a reasoning model for security work
with a 1M token context window.
You need a [Nodecode API key](https://nodecode.ai/account/keys).

First, install aider:

{% include install.md %}

Then configure your API key and endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=https://api.nodecode.ai/v1
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE https://api.nodecode.ai/v1
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Start working with aider and Nodecode on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Prefix the model name with openai/
aider --model openai/nodecode-cyber-v1
```

Aider uses the `whole` edit format for a model it doesn't know.
Cyber v1 also works with `--edit-format diff`, which sends back only the changed lines.

Aider doesn't know this model's context window or costs, so it shows a
[model warning](warnings.html) at startup.
To register them, add this to a
[`.aider.model.metadata.json` file](/docs/config/adv-model-settings.html#context-window-size-and-token-costs):

```
{
    "openai/nodecode-cyber-v1": {
        "max_tokens": 131072,
        "max_input_tokens": 1048576,
        "max_output_tokens": 131072,
        "input_cost_per_token": 0.00000033,
        "output_cost_per_token": 0.00000132,
        "cache_read_input_token_cost": 0.000000009,
        "litellm_provider": "openai",
        "mode": "chat"
    }
}
```

See the [Nodecode API docs](https://nodecode.ai/docs/cyber) for more about the API.
