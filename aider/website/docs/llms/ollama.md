---
parent: Connecting to LLMs
nav_order: 500
---

# Ollama

Aider can connect to local Ollama models.

```
# Pull the model
ollama pull <model>

# Start your ollama server
ollama serve

# In another terminal window...
python -m pip install -U aider-chat

export OLLAMA_API_BASE=http://127.0.0.1:11434 # Mac/Linux
setx   OLLAMA_API_BASE http://127.0.0.1:11434 # Windows, restart shell after setx

aider --model ollama/<model>
```


See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.

