---
parent: Connecting to LLMs
nav_order: 425
---

# CrowLLM

Aider can connect to [CrowLLM](https://crowllm.com), an OpenAI-compatible gateway that serves every supported model behind a single endpoint and a single key.

You'll need a [CrowLLM API key](https://crowllm.com).

First, install aider:

{% include install.md %}

Then point aider at the CrowLLM endpoint:

```
export OPENAI_API_BASE=https://crowllm.com/v1 # Mac/Linux
export OPENAI_API_KEY=<key>

setx OPENAI_API_BASE https://crowllm.com/v1 # Windows, restart shell after setx
setx OPENAI_API_KEY <key>
```

Start working with aider and CrowLLM on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Prefix the model id with openai/
aider --model openai/deepseek-v4-flash
```

Any model id from the gateway's public catalog works, for example
`openai/claude-opus-5-5`, `openai/glm-5.3` or `openai/gpt-6-astra`.
The catalog is keyless at <https://crowllm.com/v1/models>; ids ending in
`:free` bill at zero.

{: .tip }
CrowLLM does not require an `OPENAI_API_KEY` that belongs to OpenAI. The key
above is your CrowLLM key, and every request is routed through the gateway.
