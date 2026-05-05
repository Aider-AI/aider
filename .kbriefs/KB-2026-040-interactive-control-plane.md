# KB-2026-040: Interactive Control Plane — Interrupt and Interject During Agent Turns

**Status:** Open  
**Date:** 2026-05-03  
**Context:** Observed absence during polyglot-devcontainers OpenRewrite run; extends KB-2026-037

## Problem

KB-2026-037 documents the output gap: silence during agent turns. This KB documents
the complementary control gap: even if output were streaming, there is currently no
mechanism for the user to interrupt a running turn, inject a correction, or redirect
the agent mid-task.

During the OpenRewrite run, the agent spent ~60% of its turns in a git retry loop
(KB-2026-038). A human watching the output — had it been streaming — could have
interjected and told the agent to stop. Instead the run went to exhaustion.

## What's Missing

1. **Interrupt signal** — a keypress (e.g. `Ctrl+C` or `Ctrl+I`) that terminates the
   current provider turn cleanly and returns control to the relay.

2. **Interject prompt** — after an interrupt, the user types a correction or redirect
   that is prepended to the next turn's context before resuming.

3. **Turn boundary display** — visible markers showing when a provider turn starts and
   ends, so the user knows when interjection is safe vs. mid-turn.

4. **Pause/resume** — suspend the relay (provider stops accepting new turns) without
   killing the process, so the user can review output and decide whether to continue.

## Current Architecture Constraint

`relay_loop.py` runs the provider in a tight async loop. `ClaudeCodeProvider` awaits
`claude_agent_sdk.query()`, which is a single awaitable for the entire agent turn.
There is no internal checkpoint the relay can observe to offer a safe interruption
point within a turn.

Interrupting at the Python level (SIGINT) kills the entire process, losing the
partial session state.

## Options

**A. Turn-boundary interrupt only**

Between provider turns, `relay_loop.py` checks for a pending signal (e.g. a file
`.aider-relay/interrupt` or a keypress on stdin). If set, it prompts the user for
a correction before starting the next turn.

Safest; no mid-turn complexity. Does not help with a turn that loops indefinitely
(like the git retry case).

**B. Async stdin monitor alongside provider**

Run a concurrent `asyncio.Task` that reads stdin while the provider runs. On
`Ctrl+I`, it sets a flag the provider loop checks at its next yield point.
For SDK-based providers, the next yield point is after the full turn completes —
so this is functionally equivalent to Option A for Claude Code.

Useful for subprocess providers (Codex, AiderProvider) where the relay can send
a signal to the subprocess.

**C. Timeout-based turn segmentation**

Impose a max-turn-wall-clock (e.g. 90s). If a provider turn exceeds it, the relay
interrupts the SDK call (cancels the coroutine), writes the partial session state,
and prompts the user. Incomplete turns are flagged in `session.json`.

Prevents indefinite loops. Crude; may interrupt legitimate long-running turns.

**D. Aider UI integration (see KB-2026-041)**

Aider has a built-in pair-programming terminal UI with an input bar. If the relay
is integrated into aider's UI model rather than building its own, the interject
capability may come for free. Defer this gap to that KB.

## Recommendation

**Short term:** Option A — turn-boundary interrupt. Add a `.aider-relay/interrupt`
sentinel file check between turns. Document that users can `touch .aider-relay/interrupt`
to pause after the current turn. Cost: ~20 lines in `relay_loop.py`.

**Medium term:** Option C — per-turn timeout, configurable via `relay.sh` args.
Set a default of 120s. Prevents the git retry death spiral class of failure.

**Long term:** Option D — depend on KB-2026-041 resolution. If aider UI integration
gives us an input channel, the control plane problem largely dissolves.

## Related

- KB-2026-037: Output gap (streaming output side of the same problem)
- KB-2026-041: Aider UI integration (may subsume this KB)
- KB-2026-038: The specific run where absence of interrupt caused retry exhaustion
