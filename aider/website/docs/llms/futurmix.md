---
parent: Connecting to LLMs
nav_order: 500
---

# FuturMix

Aider can connect to [models provided by FuturMix](https://futurmix.ai), an AI Gateway that offers unified access to 22+ AI models from providers like Anthropic, OpenAI, Google, and more. FuturMix provides an OpenAI-compatible API with 99.99% SLA and competitive pricing.

You'll need a [FuturMix API key](https://futurmix.ai).

First, install aider:

{% include install.md %}

Then configure your API key and endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=https://futurmix.ai/v1
export OPENAI_API_KEY=<your-futurmix-key>

# Windows:
setx OPENAI_API_BASE https://futurmix.ai/v1
setx OPENAI_API_KEY <your-futurmix-key>
# ... restart shell after setx commands
```

Start working with aider and FuturMix on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use Claude Sonnet via FuturMix
aider --model openai/claude-sonnet-4-20250514

# Use GPT-4 via FuturMix
aider --model openai/gpt-4-turbo

# Use Gemini via FuturMix
aider --model openai/gemini-2.0-flash-exp
```

## Available Models

FuturMix supports a wide range of models through its unified gateway:

**Anthropic Claude:**
- claude-opus-4-20250514
- claude-sonnet-4-20250514
- claude-3-7-sonnet-20250219
- claude-3-5-haiku-20241022

**OpenAI:**
- gpt-4-turbo
- gpt-4o
- gpt-4o-mini
- o1
- o1-mini

**Google Gemini:**
- gemini-2.0-flash-exp
- gemini-1.5-pro
- gemini-1.5-flash

**And more from DeepSeek, xAI, and other providers.**

For a complete list of available models and pricing, visit [FuturMix's documentation](https://futurmix.ai).

## Benefits

- **Single API Key**: Access multiple AI providers through one unified endpoint
- **OpenAI Compatible**: Drop-in replacement for OpenAI API with no code changes
- **High Availability**: 99.99% SLA with automatic failover
- **Cost Effective**: Competitive pricing across all supported models
- **Easy Model Switching**: Change models by simply updating the `--model` parameter
