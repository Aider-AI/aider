---
parent: Architecture Overview
nav_order: 170
---

# File Watching Workflow

The `FileWatcher` class (`aider/watch.py`) monitors the repository for lines ending with `AI!` or `AI?`.  When a change is detected, it sets `IO.interrupt_input()` so the main prompt loop stops waiting for user input and processes the request.

```python
changes = watch(*roots, watch_filter=self.filter_func, stop_event=self.stop_event)
if self.handle_changes(changes):
    return
```

`process_changes()` gathers all AI comments from tracked files and builds a consolidated instruction block.  If any comment ends with `AI!` the coder is asked to edit the code; if it ends with `AI?` the coder answers questions.  The watch mode is often enabled automatically in IDE integrations and can be used alongside clipboard watching.

Corner cases include large files (ignored over 1MB) and paths filtered by `.gitignore` or `.aiderignore`.  The watcher runs on a background thread and can be stopped cleanly via `stop_event`.


## Stop events

Background watchers and spinners use a shared pattern for clean shutdown. Each object creates a `threading.Event` called `stop_event` and checks `is_set()` inside its loop. When the CLI or tests call the corresponding `stop()` method, the event is set so the thread can exit. `FileWatcher`, `ClipboardWatcher` (`copypaste.py`) and `WaitingSpinner` (`waiting.py`) all use this mechanism.
