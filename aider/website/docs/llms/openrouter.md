---
parent: Connecting to LLMs
nav_order: 500
---

# OpenRouter

Aider can connect to [models provided by OpenRouter](https://openrouter.ai/models?o=top-weekly):
You'll need an [OpenRouter API key](https://openrouter.ai/keys).

```
pip install aider-chat

export OPENROUTER_API_KEY=<key> # Mac/Linux
setx   OPENROUTER_API_KEY <key> # Windows

# Or any other open router model
aider --model openrouter/<provider>/<model>

# List models available from OpenRouter
aider --models openrouter/
```

In particular, Llama3 70B works well with aider, at low cost:

```
pip install aider-chat

export OPENROUTER_API_KEY=<key> # Mac/Linux
setx   OPENROUTER_API_KEY <key> # Windows

aider --model openrouter/meta-llama/llama-3-70b-instruct
```


{: .tip }
You can access Claude 3.5 Sonnet via OpenRouter, without
the tight rate limits that Anthropic applies.
Use `aider --model openrouter/anthropic/claude-3.5-sonnet`


