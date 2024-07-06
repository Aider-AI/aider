---
parent: Connecting to LLMs
nav_order: 500
---

# DeepSeek

Aider can connect to the DeepSeek.com API.
The DeepSeek Coder V2 model gets the top score on aider's code editing benchmark.

```
pip install aider-chat

export DEEPSEEK_API_KEY=<key> # Mac/Linux
setx   DEEPSEEK_API_KEY <key> # Windows

# Use DeepSeek Coder V2
aider --model deepseek/deepseek-coder
```

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.

