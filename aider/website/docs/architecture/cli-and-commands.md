---
parent: Architecture Overview
nav_order: 110
---

# CLI Entry Point and Commands

The `aider.main` module is the program entry point.  It parses command‑line arguments using `ConfigArgParse` (`aider/args.py`), sets up colors and logging, discovers the git root, and selects an initial model via `onboarding.select_default_model`.

```python
args = parse_args(sys.argv[1:])
model = select_default_model(args, io, analytics)
coder = Coder.create(main_model=model, edit_format=args.edit_format, io=io, ...)
```

If `--watch-files` or `--copy-paste` is specified, the CLI attaches a `FileWatcher` or `ClipboardWatcher` so changes in your editor or clipboard can interrupt the prompt and send new instructions. Both watchers run on background threads and share a `stop_event` so they shut down cleanly when the session ends.

The command system lives in `aider/commands.py`.  `Commands.get_commands()` registers built‑in commands (such as `/add`, `/commit`, `/undo`, `/chat-mode`) and provides tab completion support.  Custom front ends – including the optional browser UI or GUI wrappers – use the same command objects, so new interfaces can be layered on without changing the core coder logic.

During an interactive session, `Coder.run()` repeatedly calls `Coder.get_input()` to retrieve user commands or plain text messages.  The prompt can be interrupted by:

- `Control‑C` – handled in `base_coder.keyboard_interrupt()` which cancels the current LLM request and preserves pending edits.
- File or clipboard watchers – these call `IO.interrupt_input()` which stores any partially typed input and returns control to the main loop.

Both terminal and GUI/browser interfaces rely on this input loop, so adding a new front end primarily involves wiring its input and output streams into the `InputOutput` class.

