---
parent: Connecting to LLMs
nav_order: 570
---

# Github Copilot

Aider can connect to models provided by Github Copilot.
You will need to have a Github Copilot subscription.

To use Github Copilot models with Aider, you need to specify the model using the `github_copilot/` prefix.

```bash
aider --model github_copilot/claude-3.7-sonnet-thought
```

{: .tip }
> If you have not authenticated with Github Copilot before, the first time you run Aider with the `github_copilot` model, you will be prompted to authenticate with Github Copilot using device code authentication. Follow the instructions in the terminal to authenticate.

## Available Models

To see the models available via Github Copilot, run:

```bash
aider --list-models github_copilot/
```

Make sure you have access to these models through your Github Copilot subscription before attempting to use them with Aider.

# More info

For more information on Github Copilot, refer to the [official Github Copilot documentation](https://docs.github.com/en/copilot).

Also, see the
[litellm docs on Github Copilot](https://litellm.vercel.app/docs/providers/github_copilot).
