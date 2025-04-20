---
parent: Connecting to LLMs
nav_order: 300
---

# Gemini

You'll need a [Gemini API key](https://aistudio.google.com/app/u/2/apikey).

First, install aider:

{% include install.md %}

Then configure your API keys:

```bash
export GEMINI_API_KEY=<key> # Mac/Linux
setx   GEMINI_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and Gemini on your codebase:


```bash
# Change directory into your codebase
cd /to/your/project

# You can run the Gemini 2.5 Pro model with:
aider --model gemini-2.5-pro

# List models available from Gemini
aider --list-models gemini/
```

You may need to install the `google-generativeai` package. 

```bash
# If you installed with aider-install or `uv tool`
uv tool run --from aider-chat pip install google-generativeai

# Or with pipx...
pipx inject aider-chat google-generativeai

# Or with pip
pip install -U google-generativeai
```
