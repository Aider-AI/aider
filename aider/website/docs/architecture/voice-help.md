---
parent: Architecture Overview
nav_order: 160
---

# Voice Input and Offline Help

The `/voice` command uses `aider/voice.py` to record audio with the `sounddevice` library and transcribe it via `litellm.transcription` (currently OpenAI Whisper).  The resulting text is inserted into the chat as if the user had typed it.

```python
text = litellm.transcription(model="whisper-1", file=fh, prompt=history)
```

The `/help` command loads all markdown files from `aider/website` into a local vector search index (using `llama_index`).  Queries are matched against these documents and returned as context for the model.

Both features are optional extras installed via `pip install aider-chat[voice]` or `[help]`.

