---
parent: Connecting to LLMs
nav_order: 900
---

# Model warnings

{% include model-warnings.md %}


## Specifying context window size and token costs

You can register context window limits and costs for models that aren't known
to aider. Create a `.aider.models.json` file in one of these locations:

- Your home directory.
- The root if your git repo.
- The current directory where you launch aider.
- Or specify a specific file with the `--model-metadata-file <filename>` switch.


If the files above exist, they will be loaded in that order. 
Files loaded last will take priority.

The json file should be a dictionary with an entry for each model, as follows:

```
{
    "gpt-4": {
        "max_tokens": 4096, 
        "max_input_tokens": 8192,
        "max_output_tokens": 4096, 
        "input_cost_per_token": 0.00003,
        "output_cost_per_token": 0.00006,
        "litellm_provider": "openai",
        "mode": "chat",
        "supports_function_calling": true
    }
}
```

See 
[litellm's model_prices_and_context_window.json file](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) for more examples.
