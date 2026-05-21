---
parent: Connecting to LLMs
nav_order: 510
---

# NEAR AI Cloud

Aider can connect to NEAR AI Cloud TEE inference using the `nearai/` model prefix.
NEAR AI Cloud provides an OpenAI-compatible API at `https://cloud-api.near.ai/v1`.

First, install aider:

{% include install.md %}

Then configure your API key:

```
export NEARAI_API_KEY=<key> # Mac/Linux
setx   NEARAI_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and NEAR AI Cloud on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use the default TEE-backed model
aider --model nearai

# Or specify a NEAR AI Cloud model
aider --model nearai/zai-org/GLM-5.1-FP8

# List models available from NEAR AI Cloud
aider --list-models nearai/
```

You can also provide the key on the command line:

```bash
aider --model nearai/zai-org/GLM-5.1-FP8 --api-key nearai=<key>
```
