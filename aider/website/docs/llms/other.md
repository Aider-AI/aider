---
parent: Connecting to LLMs
nav_order: 800
---

# Other LLMs

Aider uses the [litellm](https://docs.litellm.ai/docs/providers) package
to connect to hundreds of other models.
You can use `aider --model <model-name>` to use any supported model.

To explore the list of supported models you can run `aider --list-models <model-name>`
with a partial model name.
If the supplied name is not an exact match for a known model, aider will
return a list of possible matching models.
For example:

```
$ aider --list-models turbo

Aider v0.29.3-dev
Models which match "turbo":
- gpt-4-turbo-preview (openai/gpt-4-turbo-preview)
- gpt-4-turbo (openai/gpt-4-turbo)
- gpt-4-turbo-2024-04-09 (openai/gpt-4-turbo-2024-04-09)
- gpt-3.5-turbo (openai/gpt-3.5-turbo)
- ...
```

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.

## LiteLLM

Aider uses the LiteLLM package to connect to LLM providers.
The [LiteLLM provider docs](https://docs.litellm.ai/docs/providers)
contain more detail on all the supported providers,
their models and any required environment variables.


## Other API key variables

Here are the API key environment variables that are supported
by litellm. See their docs for more info.

<!--[[[cog
from subprocess import run
lines = run(
    "egrep -ho '[A-Z_]+_API_KEY' ../litellm/litellm/*py | sort -u",
    shell=True,
    capture_output=True,
    text=True,
    ).stdout
lines = ['- ' + line for line in lines.splitlines(keepends=True)]
cog.out(''.join(lines))
]]]-->
- ALEPHALPHA_API_KEY
- ALEPH_ALPHA_API_KEY
- ANTHROPIC_API_KEY
- ANYSCALE_API_KEY
- AZURE_AI_API_KEY
- AZURE_API_KEY
- AZURE_OPENAI_API_KEY
- BASETEN_API_KEY
- CEREBRAS_API_KEY
- CLARIFAI_API_KEY
- CLOUDFLARE_API_KEY
- CODESTRAL_API_KEY
- COHERE_API_KEY
- CO_API_KEY
- DATABRICKS_API_KEY
- DEEPINFRA_API_KEY
- DEEPSEEK_API_KEY
- FIREWORKSAI_API_KEY
- FIREWORKS_AI_API_KEY
- FIREWORKS_API_KEY
- GEMINI_API_KEY
- GROQ_API_KEY
- HUGGINGFACE_API_KEY
- MARITALK_API_KEY
- MISTRAL_API_KEY
- NLP_CLOUD_API_KEY
- NVIDIA_NIM_API_KEY
- OLLAMA_API_KEY
- OPENAI_API_KEY
- OPENAI_LIKE_API_KEY
- OPENROUTER_API_KEY
- OR_API_KEY
- PALM_API_KEY
- PERPLEXITYAI_API_KEY
- PREDIBASE_API_KEY
- PROVIDER_API_KEY
- REPLICATE_API_KEY
- TOGETHERAI_API_KEY
- VOLCENGINE_API_KEY
- VOYAGE_API_KEY
- XINFERENCE_API_KEY
<!--[[[end]]]-->
