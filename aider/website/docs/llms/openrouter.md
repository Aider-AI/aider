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
setx   OPENROUTER_API_KEY <key> # Windows, restart shell after setx

# Or any other open router model
aider --model openrouter/<provider>/<model>

# List models available from OpenRouter
aider --models openrouter/
```

In particular, Llama3 70B works well with aider, at low cost:

```
pip install aider-chat

export OPENROUTER_API_KEY=<key> # Mac/Linux
setx   OPENROUTER_API_KEY <key> # Windows, restart shell after setx

aider --model openrouter/meta-llama/llama-3-70b-instruct
```


{: .tip }
If you get errors, check your
[OpenRouter privacy settings](https://openrouter.ai/settings/privacy).
Be sure to "enable providers that may train on inputs"
to allow use of all models.



