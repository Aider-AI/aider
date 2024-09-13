---
parent: Configuration
nav_order: 950
description: Configuring advanced settings for LLMs.
---

# Advanced model settings

## Context window size and token costs

In most cases, you can safely ignore aider's warning about unknown context
window size and model costs.

But, you can register context window limits and costs for models that aren't known
to aider. Create a `.aider.model.metadata.json` file in one of these locations:

- Your home directory.
- The root if your git repo.
- The current directory where you launch aider.
- Or specify a specific file with the `--model-metadata-file <filename>` switch.


If the files above exist, they will be loaded in that order. 
Files loaded last will take priority.

The json file should be a dictionary with an entry for each model, as follows:

```
{
    "deepseek/deepseek-chat": {
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

{: .tip }
Use a fully qualified model name with a `provider/` at the front
in the `.aider.model.metadata.json` file.
For example, use `deepseek/deepseek-chat`, not just `deepseek-chat`.

## Model settings

Aider has a number of settings that control how it works with
different models.
These model settings are pre-configured for most popular models.
But it can sometimes be helpful to override them or add settings for
a model that aider doesn't know about.

To do that,
create a `.aider.model.settings.yml` file in one of these locations:

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
  reminder: sys
  examples_as_sys_msg: false
- name: "gpt-4-turbo-2024-04-09"
  edit_format: "udiff"
  weak_model_name: "gpt-3.5-turbo"
  use_repo_map: true
  send_undo_reply: true
  accepts_images: true
  lazy: true
  reminder: sys
  examples_as_sys_msg: false
```

You can look at the `ModelSettings` class in
[models.py](https://github.com/paul-gauthier/aider/blob/main/aider/models.py)
file for details about all of the model setting that aider supports.
That file also contains the settings for many popular models.

