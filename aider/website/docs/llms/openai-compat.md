---
parent: Connecting to LLMs
nav_order: 500
---

# OpenAI compatible APIs

Aider can connect to any LLM which is accessible via an OpenAI compatible API endpoint.

First, install aider:

{% include install.md %}

Then configure your API key and endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=<endpoint>
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE <endpoint>
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Start working with aider and your OpenAI compatible API on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Prefix the model name with openai/
aider --model openai/<model-name>
```

Use the API base URL, including any path prefix required by the server.
For example, if its chat endpoint is
`http://localhost:8000/team/v1/chat/completions`, set the base URL to
`http://localhost:8000/team/v1`, without `/chat/completions`.

You can also select the base URL for one Aider session without changing a
persistent environment variable:

```bash
aider --model openai/<model-name> --openai-api-base http://localhost:8000/team/v1
```

This changes the endpoint, not the model's capabilities or generation settings.
For server-specific request parameters, use the model's `extra_params` in a
[model settings file](/docs/config/adv-model-settings.html).

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.
