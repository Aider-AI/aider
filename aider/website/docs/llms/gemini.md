---
parent: Connecting to LLMs
nav_order: 300
---

# Gemini

You'll need a [Gemini API key](https://aistudio.google.com/app/u/2/apikey).

```
python -m pip install -U aider-chat

# You may need to install google-generativeai
pip install -U google-generativeai

# Or with pipx...
pipx inject aider-chat google-generativeai

export GEMINI_API_KEY=<key> # Mac/Linux
setx   GEMINI_API_KEY <key> # Windows, restart shell after setx

# You can run the Gemini 2.5 Pro model with:
aider --model gemini-2.5-pro

# List models available from Gemini
aider --list-models gemini/
```

