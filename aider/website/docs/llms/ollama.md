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

You can set the Ollama server's context window with a 
[`.aider.model.settings.yml` file](https://aider.chat/docs/config/adv-model-settings.html#model-settings)
like this:

```
- name: aider/extra_params
  extra_params:
    num_ctx: 65536
```

That uses the special model name `aider/extra_params` to set it for *all* models. You should probably use a specific model name like:

```
- name: ollama_chat/qwen2.5-coder:32b-instruct-fp16
  extra_params:
    num_ctx: 65536
```

