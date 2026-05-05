# KB-2026-037: Provider Streaming Output Gap

**Status:** Open  
**Date:** 2026-05-02  
**Context:** Observed during first live relay run against polyglot-devcontainers

## Gap

While a provider is working, the aider-relay terminal shows nothing. The user
sees silence for minutes, then a burst of `[tool: ...]` lines (or nothing at
all) when Claude finishes a turn.

## Root Cause

`ClaudeCodeProvider` pulls events from `claude_agent_sdk.query()`, which yields
message-level objects — `AssistantMessage`, `ResultMessage`, `RateLimitEvent`.
Claude Code's internal tool calls (Read, Bash, Edit, Write) happen inside the
SDK invocation and do not surface as individual stream events. Only the final
assistant turn produces output the relay can print.

Relay loop handler (`relay_loop.py:run_turn`) is correctly wired for streaming
— it prints `text` events as they arrive — but there is almost nothing to print
during a long agentic turn.

## Options

**1. Heartbeat line** (trivial)  
Print a `.` or elapsed-time line every N seconds while `run_turn` is awaiting.
No new information; prevents the user from wondering if the process is hung.

**2. Surface SDK event types currently ignored**  
Audit all message types returned by `claude_agent_sdk.query()` (system
messages, tool result messages, etc.). If any carry useful progress signals,
yield them as `text` events. Low risk; may yield little depending on SDK
internals.

**3. Subprocess stdout passthrough** (richest output)  
Invoke `claude` as a raw subprocess and pipe its stdout directly to the relay
terminal. This surfaces the full tool-call trace visible when running `claude`
interactively. Exhaustion signal must be parsed from CLI output rather than
from SDK events. Couples the provider to Claude Code's CLI output format —
brittle if that format changes.

## Recommendation

Implement option 1 immediately (cheap, removes anxiety). Investigate option 2
before committing to option 3. Only pursue option 3 if the SDK emits nothing
useful — subprocess coupling has ongoing maintenance cost.

## Decision Needed

Which option(s) to implement, and whether to do this before or after the first
relay experiment produces results. Observing a live run first may reveal
whether silence is actually a problem in practice.
