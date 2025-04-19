---
parent: Troubleshooting
nav_order: 28
---

# Models and API keys

Aider needs to know which LLM model you would like to work with and which keys
to provide when accessing it via API.

## Defaults

If you don't explicitly name a model, aider will try to select a model
for you to work with.

First, aider will check which 
[keys you have provided via the environment, config files, or command line arguments](https://aider.chat/docs/config/api-keys.html).
Based on the available keys, aider will select the best model to use.

If you have not provided any keys, aider will offer to help you connect to 
[OpenRouter](http://openrouter.ai)
which provides both free and paid access to most popular LLMs.
Once connected, aider will select the best model available on OpenRouter
based on whether you have a free or paid account there.

## Specifying model & key

You can also tell aider which LLM to use and provide an API key.
The easiest way is to use the `--model` and `--api-key`
command line arguments, like this:

```
# Work with DeepSeek via DeepSeek's API
aider --model deepseek --api-key deepseek=your-key-goes-here

# Work with Claude 3.7 Sonnet via Anthropic's API
aider --model sonnet --api-key anthropic=your-key-goes-here

# Work with o3-mini via OpenAI's API
aider --model o3-mini --api-key openai=your-key-goes-here

# Work with Sonnet via OpenRouter's API
aider --model openrouter/anthropic/claude-3.7-sonnet --api-key openrouter=your-key-goes-here

# Work with DeepSeek Chat V3 via OpenRouter's API
aider --model openrouter/deepseek/deepseek-chat --api-key openrouter=your-key-goes-here
```

For more information, see the documentation sections:

- [Connecting to LLMs](https://aider.chat/docs/llms.html)
- [Configuring API keys](https://aider.chat/docs/config/api-keys.html)
