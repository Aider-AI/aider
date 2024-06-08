---
parent: Configuration
nav_order: 900
description: Using a .env file to store LLM API keys for aider.
---

# Storing LLM params in .env 

You can use a `.env` file to store API keys and other settings for the
models you use with aider.
You currently can not set general aider options
in the `.env` file, only LLM environment variables.

Aider will look for a `.env` file in the
root of your git repo or in the current directory.
You can give it an explicit file to load with the `--env-file <filename>` parameter.

Here is an example `.env` file:

```
OPENAI_API_KEY=<key>
ANTHROPIC_API_KEY=<key>
GROQ_API_KEY=<key>
OPENROUTER_API_KEY=<key>

AZURE_API_KEY=<key>
AZURE_API_VERSION=2023-05-15
AZURE_API_BASE=https://example-endpoint.openai.azure.com

OLLAMA_API_BASE=http://127.0.0.1:11434
```
