---
parent: Connecting to LLMs
nav_order: 200
---

# Anthropic

To work with Anthropic's models, you need to provide your
[Anthropic API key](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
either in the `ANTHROPIC_API_KEY` environment variable or
via the `--anthropic-api-key` command line switch.

Aider has some built in shortcuts for the most popular Anthropic models and
has been tested and benchmarked to work well with them:

```
python -m pip install aider-chat

export ANTHROPIC_API_KEY=<key> # Mac/Linux
setx   ANTHROPIC_API_KEY <key> # Windows, restart shell after setx

# Aider uses Claude 3.5 Sonnet by default (or use --sonnet)
aider

# Claude 3 Opus
aider --opus

# List models available from Anthropic
aider --models anthropic/
```

{: .tip }
Anthropic has very low rate limits.
You can access all the Anthropic models via
[OpenRouter](openrouter.md)
without rate limits.
For example: `aider --model openrouter/anthropic/claude-3.5-sonnet`

You can use `aider --model <model-name>` to use any other Anthropic model.
For example, if you want to use a specific version of Opus
you could do `aider --model claude-3-opus-20240229`.

## Claude on Vertex AI

To work with Anthropic's models on Vertex AI, you need to install the
[gcloud CLI](https://cloud.google.com/sdk/docs/install) and [login](https://cloud.google.com/sdk/docs/initializing) with a GCP account
or service account with permission to use the Vertex AI API.

With your chosen login method, the gcloud CLI should automatically set the
`GOOGLE_APPLICATION_CREDENTIALS` environment variable which points to the credentials file.

To configure Aider to use the Vertex AI API, you need to set `VERTEXAI_PROJECT` (the GCP project ID)
and `VERTEXAI_LOCATION` (the GCP region) [environment variables for Aider](/docs/config/dotenv.html).

Note that Claude on Vertex AI is only available in certain GCP regions, check [the model card](https://console.cloud.google.com/vertex-ai/publishers/anthropic/model-garden/claude-3-5-sonnet) for your model to see which regions are supported.

Example `.env` file:

```
VERTEXAI_PROJECT=my-project
VERTEXAI_LOCATION=us-east5
```

Now in your [Aider config](/docs/config/aider_conf.html) set the model to any of the Anthropic models supported by Vertex AI.

Example `.aider.conf.yml` file:

```yaml
model: vertex_ai/claude-3-5-sonnet@20240620
```

Or use the `--model` command line switch:
```
aider --model vertex_ai/claude-3-5-sonnet@20240620
```

Note that the Aider built in shortcuts (`aider --opus`) for the most popular Anthropic models will not work with Vertex Anthropic models.