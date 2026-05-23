---
parent: Connecting to LLMs
nav_order: 450
---

# Hugging Face Inference Providers

Aider can connect to [Hugging Face Inference Providers](https://huggingface.co/docs/inference-providers/) using the OpenAI-compatible client. Inference Providers gives you access to multiple AI providers through a single OpenAI-compatible API.

You'll need a [Hugging Face account](https://huggingface.co/join) and an [access token](https://huggingface.co/settings/tokens).

First, install aider:

{% include install.md %}

Then configure your API key and base URL:

```
# Mac/Linux:
export OPENAI_API_BASE=https://router.huggingface.co/v1
export HUGGINGFACE_API_KEY=<your-hf-token>

# Windows:
setx OPENAI_API_BASE https://router.huggingface.co/v1
setx HUGGINGFACE_API_KEY <your-hf-token>
# ... restart shell after setx commands
```

**Note:** `OPENAI_API_BASE` is required because Hugging Face Inference Providers uses an OpenAI-compatible endpoint. You can also use `HF_TOKEN` instead of `HUGGINGFACE_API_KEY`.

Start working with aider on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use any model from Inference Providers
# Prefix the model name with huggingface/
aider --model huggingface/<model-name>

# Using MiniMaxAI/MiniMax-M2:
aider --model huggingface/MiniMaxAI/MiniMax-M2
```

## Selecting a specific provider

By default, Inference Providers automatically routes requests to the best available provider. If you want to use a specific provider you can append the provider name to the model:

```bash
aider --model huggingface/<model-name>:<provider>

# Using GLM-4.6 via zai-org provider:
aider --model huggingface/zai-org/GLM-4.6:zai-org
```

You can also use `:cheapest` or `:fastest` to automatically select based on cost or throughput:

```bash
# Use the cheapest available provider:
aider --model huggingface/MiniMaxAI/MiniMax-M2:cheapest

# Use the fastest available provider:
aider --model huggingface/MiniMaxAI/MiniMax-M2:fastest
```

You can find the provider-specific syntax on any model card's "Use this model" → "Inference Providers" section.

## Finding models

You can discover models available via Inference Providers in several ways:

1. **Browse models on Hugging Face**: Visit [models with Inference Providers](https://huggingface.co/models?pipeline_tag=text-generation&inference_provider=all&sort=trending) to see all models with at least one Inference Provider hosting them.

2. **From model cards**: On any model card page (like [zai-org/GLM-4.6](https://huggingface.co/zai-org/GLM-4.6)), click "Use this model" → "Inference Providers" to see the code snippet with the exact model name.

3. **See the docs**: Check the [Inference Providers Hub API docs](https://huggingface.co/docs/inference-providers/hub-api) for programmatic model discovery

## More information

- [Inference Providers documentation](https://huggingface.co/docs/inference-providers/)
- [Pricing details](https://huggingface.co/docs/inference-providers/pricing)
- [Supported providers](https://huggingface.co/docs/inference-providers/index#partners)
