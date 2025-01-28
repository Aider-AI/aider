---
parent: Connecting to LLMs
nav_order: 500
---

# DeepSeek

Aider can connect to the DeepSeek.com API.
To work with DeepSeek's models, you need to set the `DEEPSEEK_API_KEY` environment variable with your [DeepSeek API key](https://platform.deepseek.com/api_keys).  
The DeepSeek Chat V3 model has a top score on aider's code editing benchmark.

```
python -m pip install -U aider-chat

export DEEPSEEK_API_KEY=<key> # Mac/Linux
setx   DEEPSEEK_API_KEY <key> # Windows, restart shell after setx

# Use DeepSeek Chat v3
aider --deepseek
```

