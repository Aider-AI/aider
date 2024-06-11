---
parent: Connecting to LLMs
nav_order: 900
---

# Model warnings

{% include model-warnings.md %}


## Adding settings for missing models
You can register model settings used by aider for unknown models. 
Create a `.aider.models.yml` file in one of these locations:

- Your home directory.
- The root if your git repo.
- The current directory where you launch aider.
- Or specify a specific file with the `--model-settings-file <filename>` switch.

If the files above exist, they will be loaded in that order. 
Files loaded last will take priority.

The yaml file should be a a list of dictionary objects for each model, as follows:

```
- name: "gpt-3.5-turbo"
  edit_format: "whole"
  weak_model_name: "gpt-3.5-turbo"
  use_repo_map: false
  send_undo_reply: false
  accepts_images: false
  lazy: false
  reminder_as_sys_msg: true
  examples_as_sys_msg: false
- name: "gpt-4-turbo-2024-04-09"
  edit_format: "udiff"
  weak_model_name: "gpt-3.5-turbo"
  use_repo_map: true
  send_undo_reply: true
  accepts_images: true
  lazy: true
  reminder_as_sys_msg: true
  examples_as_sys_msg: false
```

## Specifying context window size and token costs

You can register context window limits and costs for models that aren't known
to aider. Create a `.aider.litellm.models.json` file in one of these locations:

- Your home directory.
- The root if your git repo.
- The current directory where you launch aider.
- Or specify a specific file with the `--model-metadata-file <filename>` switch.


If the files above exist, they will be loaded in that order. 
Files loaded last will take priority.

The json file should be a dictionary with an entry for each model, as follows:

```
{
    "deepseek-chat": {
        "max_tokens": 4096,
        "max_input_tokens": 32000,
        "max_output_tokens": 4096,
        "input_cost_per_token": 0.00000014,
        "output_cost_per_token": 0.00000028,
        "litellm_provider": "deepseek",
        "mode": "chat"
    }
}
```

See 
[litellm's model_prices_and_context_window.json file](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json) for more examples.
