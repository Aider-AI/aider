---
parent: Connecting to LLMs
nav_order: 500
---

# Azure

Aider can connect to the OpenAI models on Azure.

```
python -m pip install -U aider-chat

# Mac/Linux:                                           
export AZURE_API_KEY=<key>
export AZURE_API_VERSION=2024-12-01-preview
export AZURE_API_BASE=https://myendpt.openai.azure.com

# Windows
setx AZURE_API_KEY <key>
setx AZURE_API_VERSION 2024-12-01-preview
setx AZURE_API_BASE https://myendpt.openai.azure.com
# ... restart your shell after setx commands

aider --model azure/<your_model_deployment_name>

# List models available from Azure
aider --list-models azure/
```

Note that aider will also use environment variables
like `AZURE_OPENAI_API_xxx`.

The `aider --list-models azure/` command will list all models that aider supports through Azure, not the models that are available for the provided endpoint.

When setting the model to use with `--model azure/<your_model_deployment_name>`, `<your_model_deployment_name>` is likely just the name of the model you have deployed to the endpoint for example `o3-mini` or `gpt-4o`.  The screenshow below shows `o3-mini` and `gpt-4o` deployments in the Azure portal done under the `myendpt` resource.

![example azure deployment](/assets/azure-deployment.png)