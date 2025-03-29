---
parent: Connecting to LLMs
nav_order: 570
---

# Github Copilot

Aider can connect to models provided by Github Copilot.
You will need to have a Github Copilot subscription.

To use Github Copilot models with aider, you need to specify the model using the `github_copilot/` prefix.

```bash
aider --model github_copilot/claude-3.7-sonnet-thought
```

{: .tip }
> If you have not authenticated with Github Copilot before, the first time you run aider with the `github_copilot` model, you will be prompted to authenticate with Github Copilot using device code authentication. Follow the instructions in the terminal to authenticate.


# More info

For more information on Github Copilot, refer to the [official Github Copilot documentation](https://docs.github.com/en/copilot).

