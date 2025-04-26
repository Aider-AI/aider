---
parent: Connecting to LLMs
nav_order: 400
---

# LM Studio

Aider can connect to models served by LM Studio.

First, install aider:

{% include install.md %}

Then configure your API key and endpoint:

```
# Must set a value here even if its a dummy value
export LM_STUDIO_API_KEY=dummy-api-key # Mac/Linux
setx   LM_STUDIO_API_KEY dummy-api-key # Windows, restart shell after setx

# LM Studio default server URL is http://localhost:1234/v1
export LM_STUDIO_API_BASE=http://localhost:1234/v1 # Mac/Linux
setx   LM_STUDIO_API_BASE http://localhost:1234/v1 # Windows, restart shell after setx
```

**Note:** Even though LM Studio doesn't require an API Key out of the box the `LM_STUDIO_API_KEY` must have a dummy value like `dummy-api-key` set or the client request will fail trying to send an empty `Bearer` token.

Start working with aider and LM Studio on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

aider --model lm_studio/<your-model-name>
```

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.
