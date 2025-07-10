---
parent: Architecture Overview
nav_order: 120
---

# Memory and Context Management

Aider must fit messages, repo summaries, and edits into the model's context window.  Each `Model` (from `aider/models.py`) specifies its max input tokens.  The coder computes `max_chat_history_tokens` as roughly one sixteenth of that size and triggers summarization when the conversation grows beyond this limit.

## Summarizing Chat History

`ChatSummary` (`aider/history.py`) runs in a background thread.  When launched via `Coder.summarize_start()`, it condenses `done_messages` into a shorter summary:

```python
def summarize_worker(self):
    self.summarizing_messages = list(self.done_messages)
    self.summarized_done_messages = self.summarizer.summarize(self.summarizing_messages)
```

After summarization finishes, the summary replaces the older messages so the coder can continue chatting without exceeding the token budget.  The total tokens sent and received are tracked for cost reporting.

## Repository Map

`RepoMap` (`aider/repomap.py`) generates concise summaries of files and their key symbols.  At runtime `Coder.get_repo_map()` selects only the most relevant portions based on the current conversation and `--map-tokens` budget.  This gives the model enough context to understand dependencies without exceeding the prompt limit.

## Restoring History Across Sessions

With the `--restore-chat-history` option, the markdown transcript from the previous run is read from `chat_history.md`.  The messages are loaded into `done_messages` on startup and summarized before the first prompt.  This allows long‑running projects to pick up where they left off even after the process exits.

