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

aider --model ollama_chat/<model>
```

{: .note }
Using `ollama_chat/` is recommended over `ollama/`.


See the [model warnings](warnings.html)
section for information on warnings which will occur
when working with models that aider is not familiar with.

## API Key

If you are using an ollama that requires an API key you can set `OLLAMA_API_KEY`:

```
export OLLAMA_API_KEY=<api-key> # Mac/Linux
setx   OLLAMA_API_KEY <api-key> # Windows, restart shell after setx
```

## Setting the context window size

[Ollama uses a 2k context window by default](https://github.com/ollama/ollama/blob/main/docs/faq.md#how-can-i-specify-the-context-window-size),
which is very small for working with aider.

Aider sets Ollama's context window to 8k by default. 
If you would like
a larger context window
you can use a
[`.aider.model.settings.yml` file](https://aider.chat/docs/config/adv-model-settings.html#model-settings)
like this:

```
- name: ollama/qwen2.5-coder:32b-instruct-fp16
  extra_params:
    num_ctx: 8192
```

Unlike most other LLM servers, Ollama does not throw an error if you submit
a request that exceeds the context window.
Instead, it just silently truncates the request by discarding the "oldest" messages
in the chat to make it fit within the context window.
So if your context window is too small, you won't get an error.
Aider will probably just fail to work well and experience
a lot of 
[file editing problems](https://aider.chat/docs/troubleshooting/edit-errors.html).
