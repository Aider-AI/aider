---
parent: Connecting to LLMs
nav_order: 400
---

# LM Studio

To use LM Studio:

```
python -m pip install -U aider-chat

export LM_STUDIO_API_KEY=<key> # Mac/Linux
setx   LM_STUDIO_API_KEY <key> # Windows, restart shell after setx

export LM_STUDIO_API_BASE=<url> # Mac/Linux
setx   LM_STUDIO_API_BASE <url> # Windows, restart shell after setx

aider --model lm_studio/<your-model-name>
```


