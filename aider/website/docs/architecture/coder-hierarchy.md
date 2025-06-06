---
parent: Architecture Overview
nav_order: 100
---

# Coder Hierarchy and Prompt Lifecycle

Aider organizes its prompting logic around a set of `Coder` classes located in `aider/coders/`.  The base class `base_coder.py` manages common behavior such as tracking files in chat, running commands, and interacting with the LLM.  The `Coder.create()` factory picks an appropriate subclass based on the chosen edit format or chat mode.

```bash
aider/coders/
├── base_coder.py
├── ask_coder.py
├── architect_coder.py
├── patch_coder.py
└── ...
```

Each subclass tailors the prompting strategy:

- **AskCoder** – lightweight Q&A style interactions with minimal code editing.
- **ArchitectCoder** – sends the user request to an architect model for high‑level planning and then forwards instructions to an editor model.
- **PatchCoder**, **WholeCoder**, **DiffCoder** – return edits in the corresponding edit format.

`Coder.create()` migrates chat history, open files, and other context when switching modes so the conversation continues smoothly.

## Prompt Grouping

`ChatChunks` (`aider/chat_chunks.py`) collects system messages, repo summaries, examples, read‑only files and prior chat history.  These are assembled into a consistent order before sending to the LLM:

```python
chunks.add_system(system_msg)
chunks.add_examples(example_msgs)
chunks.add_repo(repo_map)
chunks.add_readonly(readonly_files)
chunks.add_chat_files(in_chat_files)
chunks.add_history(history_msgs)
```

Some chunks are marked cacheable, enabling providers that support prompt caching to reuse them.

## Tool Calls and Multi‑step Replies

Models can return tool calls (function calls in OpenAI style) to request additional files.  The coder parses these requests and replies with the relevant file contents before applying any edits.  Architect mode chains multiple models: the architect model replies with plain text instructions which are then passed to an editor coder that produces the final diff or whole‑file edits.

```
User → Architect model → instructions → Editor model → code edits
```

The coder also supports incremental output for models with the "infinite output" capability.  Partial responses are resent with `supports_assistant_prefill` so the model continues generating beyond its normal token limit.

