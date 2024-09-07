---
parent: Connecting to LLMs
nav_order: 550
---

# Vertex AI

Aider can connect to models provided by Google Vertex AI.
You will need to install the
[gcloud CLI](https://cloud.google.com/sdk/docs/install) and [login](https://cloud.google.com/sdk/docs/initializing) with a GCP account
or service account with permission to use the Vertex AI API.

With your chosen login method, the gcloud CLI should automatically set the
`GOOGLE_APPLICATION_CREDENTIALS` environment variable which points to the credentials file.

To configure Aider to use the Vertex AI API, you need to set `VERTEXAI_PROJECT` (the GCP project ID)
and `VERTEXAI_LOCATION` (the GCP region) [environment variables for Aider](/docs/config/dotenv.html).

Note that Claude on Vertex AI is only available in certain GCP regions, 
check [the model card](https://console.cloud.google.com/vertex-ai/publishers/anthropic/model-garden/claude-3-5-sonnet) 
for your model to see which regions are supported.

Example `.env` file:

```
VERTEXAI_PROJECT=my-project
VERTEXAI_LOCATION=us-east5
```

Then you can run aider with the `--model` command line switch, like this:

```
aider --model vertex_ai/claude-3-5-sonnet@20240620
```

Or you can use the [yaml config](/docs/config/aider_conf.html) to set the model to any of the 
models supported by Vertex AI.

Example `.aider.conf.yml` file:

```yaml
model: vertex_ai/claude-3-5-sonnet@20240620
```
