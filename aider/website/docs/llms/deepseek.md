---
parent: Connecting to LLMs
nav_order: 500
---

# DeepSeek

Aider can connect to the DeepSeek.com API.
The DeepSeek Coder V2 model has a top score on aider's code editing benchmark.

```
python -m pip install -U aider-chat

export DEEPSEEK_API_KEY=<key> # Mac/Linux
setx   DEEPSEEK_API_KEY <key> # Windows, restart shell after setx

# Use DeepSeek Coder V2
aider --deepseek
```

