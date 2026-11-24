---
parent: Connecting to LLMs
nav_order: 510
description: Use Ace Data Cloud with Aider's OpenAI-compatible configuration.
---

# Ace Data Cloud

Connect to Ace Data Cloud with Aider's [OpenAI-compatible configuration](openai-compat.html). Create an [application API token](https://platform.acedata.cloud/console/applications) that is permitted to use Chat Completions. Check the [model catalog](https://platform.acedata.cloud/models) for current compatible model IDs and prices.

In a shell dedicated to the Ace Data Cloud connection, set `OPENAI_API_KEY` to your Ace Data Cloud application token. Then set the endpoint and choose an exact model ID:

```bash
export OPENAI_API_BASE=https://api.acedata.cloud/v1

aider --model openai/gpt-4.1-mini
```

On Windows, set the same environment variables using the instructions in the OpenAI-compatible configuration guide. Replace `gpt-4.1-mini` with the ID of another catalog model that supports Chat Completions and that your account can access. Set model settings for context or edit format only when you have verified them for the selected model.
