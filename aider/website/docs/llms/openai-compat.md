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

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.

## Fikra API

Fikra is an OpenAI-compatible inference API serving DeepSeek, GLM and Kimi models, among others. Get an API key from [fikraapi.co.ke](https://fikraapi.co.ke), then:

```
# Mac/Linux:
export OPENAI_API_BASE=https://fikraapi.co.ke/v1
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE https://fikraapi.co.ke/v1
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Start working with aider and Fikra on your codebase:

```bash
# Prefix the model name with openai/
aider --model openai/deepseek-v4.1-flash
```

Fikra's headline model is DeepSeek V4.1 Flash, at $0.045 per 1M input tokens and $0.09 per 1M output tokens, with a 1M token context. The October 17 build (id `deepseek-v4.1-flash-1017`) is priced at $0.05/$0.11.

Fikra also serves GLM 5.3, GLM 5.3 Flash, GLM 5.2, Kimi K3, StepFun Step 5, Qwen 3.8 27B (cached input $0.10/M), Xiaomi MiMo V2.6 Pro, NVIDIA Nemotron 3.5 Super VL, plus Fikra house lanes. The full catalog is at https://fikraapi.co.ke/v1/models and https://fikraapi.co.ke. Per-token USD, $1 minimum top-up, M-Pesa and card payment.
