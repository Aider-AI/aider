---
parent: Connecting to LLMs
nav_order: 100
---

# OpenAI

To work with OpenAI's models, you need to provide your
[OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key)
either in the `OPENAI_API_KEY` environment variable or
via the `--api-key openai=<key>` command line switch.

Aider has some built in shortcuts for the most popular OpenAI models and
has been tested and benchmarked to work well with them:

```
python -m pip install -U aider-chat

# o3-mini
aider --model o3-mini --api-key openai=<key>

# o1-mini
aider --model o1-mini --api-key openai=<key>

# GPT-4o
aider --model gpt-4o --api-key openai=<key>

# List models available from OpenAI
aider --list-models openai/

# You can also store you API key in environment variables (or .env)
export OPENAI_API_KEY=<key> # Mac/Linux
setx   OPENAI_API_KEY <key> # Windows, restart shell after setx
```

You can use `aider --model <model-name>` to use any other OpenAI model.
For example, if you want to use a specific version of GPT-4 Turbo
you could do `aider --model gpt-4-0125-preview`.

## Reasoning models from other providers

Many of OpenAI's 
"reasoning" models have restrictions on streaming and setting the temperature parameter.
Some also support different levels of "reasoning effort".
Aider is configured to work properly with these models
when served through major provider APIs and
has a `--reasoning-effort` setting.

You may need to [configure reasoning model settings](/docs/config/reasoning.html)
if you are using them through another provider
and see errors related to temperature or system prompt.
