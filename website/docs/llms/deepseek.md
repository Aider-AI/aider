---
parent: Connecting to LLMs
nav_order: 500
---

# Deepseek

Aider can connect to the Deepseek.com API.
Deepseek appears to grant 5M tokens of free API usage to new accounts.

```
pip install aider-chat

export DEEPSEEK_API_KEY=<key> # Mac/Linux
setx   DEEPSEEK_API_KEY <key> # Windows

# Use Deepseek Chat v2
aider --model deepseek/deepseek-chat
```

See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.

