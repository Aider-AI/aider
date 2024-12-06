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

aider --model gemini/gemini-1.5-pro-latest

# List models available from Gemini
aider --list-models gemini/
```

