---
parent: Architecture Overview
nav_order: 130
---

# Session Resumption and Interrupt Handling

Long running edits can be interrupted with `Control‑C`.  When the user sends the interrupt while a model reply is streaming, `base_coder.send_messages()` catches `KeyboardInterrupt` and stops waiting for the response.  The partial text already received stays in the conversation so you can clarify or retry.

If a second `Control‑C` arrives within two seconds, `keyboard_interrupt()` exits immediately.  Otherwise it displays `^C again to exit` and returns to the input loop with any pending edits preserved.

```python
except KeyboardInterrupt:
    interrupted = True
    break
```

Aider also resumes gracefully if the process exits.  When `--restore-chat-history` is enabled, `InputOutput.read_text(chat_history_file)` loads the previous markdown transcript and `Coder.summarize_start()` condenses it to fit the new session's token budget.  Pending edits are stored in the git working tree; they will be committed on the next successful run.

