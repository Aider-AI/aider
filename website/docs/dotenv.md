---
parent: Configuration
nav_order: 900
description: Using a .env file to store LLM API keys for aider.
---

# Storing LLM params in .env 

You can use a `.env` file to store API keys and other settings for the
models you use with aider.
You currently can not set general aider options
in the `.env` file, only LLM environment variables.

{% include special-keys.md %}

Aider will look for a `.env` file in the
root of your git repo or in the current directory.
You can give it an explicit file to load with the `--env-file <filename>` parameter.

Here is an example `.env` file:

```dotenv
[[[cog
from aider.args import get_sample_dotenv
print(get_sample_dotenv())
]]]
```
