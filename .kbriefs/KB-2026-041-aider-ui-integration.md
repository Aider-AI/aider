# KB-2026-041: Aider Pair-Programming UI Integration

**Status:** Open  
**Date:** 2026-05-03  
**Context:** Identified as structural gap after polyglot-devcontainers OpenRewrite run

## Problem

Aider ships a terminal pair-programming UI: an input bar, streaming diff display,
token/cost tracking, and inline confirmation prompts. The relay currently bypasses
all of this — it invokes aider's `Coder` object directly (AiderProvider) or routes
around aider entirely (ClaudeCodeProvider, CodexProvider).

The result is a relay that has weaker UX than running aider directly: no live diffs,
no cost display, no confirmation flow, and no input channel (see KB-2026-040).

## What Aider's UI Provides

From the aider codebase (`InputOutput`, `commands.py`, `mdstream.py`):

- **Input bar**: readline-based prompt with history. Users can type at any point;
  aider queues the input and injects it at the next safe boundary.
- **Streaming output**: aider streams the model's response token-by-token to the
  terminal using `mdstream.py` (Markdown-aware).
- **Diff display**: after each edit, aider shows a unified diff of the changes.
- **Token/cost tracking**: displayed in the prompt suffix after each turn.
- **Confirmation prompts**: shell command execution requires explicit user `y/n`
  (controlled by `InputOutput.yes` and `explicit_yes_required`).
- **`/commands`**: user can type `/undo`, `/drop`, `/add`, `/ask`, `/diff` etc.
  mid-session.

## Integration Options

**A. Surface relay as an aider `/command`**

Add a `/relay` slash command to aider's command set. Running inside a normal
`aider` session, the user types `/relay` to hand off to a second provider when
the first is exhausted. The relay logic runs inside the existing aider session
and inherits the full UI.

Requires forking `aider/commands.py`. Natural fit for the hard-fork model of
this project.

**B. Use aider as the primary UI; relay as a provider multiplexer underneath**

Invert the current architecture: aider's `main()` is the entry point and UI host.
The relay's provider-switching logic is a drop-in replacement for aider's model
selection, triggered by exhaustion signals. The user always interacts through
aider's terminal UI.

Most idiomatic. Requires understanding aider's `Coder` lifecycle and how it
selects and switches models. AiderProvider already wraps Coder — this extends
that in the opposite direction.

**C. Build a relay-native TUI using `textual` or `prompt_toolkit`**

Implement a standalone terminal UI for the relay, separate from aider's. Provides
full control; does not benefit from aider's existing UI investment.

High cost. Only justified if the relay needs to diverge significantly from aider's
UX model.

**D. Thin wrapper: pipe aider's stdout and expose its stdin**

Run `aider` as a subprocess with `--no-pretty` and connect its stdin/stdout to
the relay terminal. The relay monitors aider's output for exhaustion signals and
injects the handoff prompt into stdin.

Low implementation cost. Fragile: depends on aider's text output format. Does not
give programmatic access to turn boundaries or diffs.

## Research Needed

Before choosing an option, understand:

1. `aider/main.py` — entry point and session lifecycle
2. `aider/io.py` (`InputOutput`) — how aider reads user input and dispatches to
   commands; specifically whether there is a plugin point for external input sources
3. `aider/commands.py` — how slash commands are registered and dispatched
4. `aider/coders/base_coder.py` — `run_one()` and `send_message()` turn lifecycle;
   where the model boundary sits and how switching would work
5. `aider/mdstream.py` — streaming output; whether it can be replaced or redirected

## Recommendation

**Research first** (one KBPD cycle): read the five files above and fill in this KB
with concrete entry points and plugin boundaries before committing to an option.

**Likely target:** Option B — relay as model multiplexer underneath aider's UI.
AiderProvider already wraps Coder; the question is whether the relay can intercept
aider's model dispatch cleanly enough to inject provider switching without forking
the core run loop.

**If Option B is not feasible:** Option A — `/relay` command. Narrower scope,
lower risk, still gives the user aider's full UI for the session.

## Related

- KB-2026-029: AiderProvider design (existing aider-as-provider analysis)
- KB-2026-030: Aider integration plan
- KB-2026-040: Interactive control plane (may be subsumed by this KB)
- KB-2026-037: Provider streaming output gap
