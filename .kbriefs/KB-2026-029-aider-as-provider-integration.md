---
id: KB-2026-029
type: integration-spec
status: active
created: 2026-04-30
updated: 2026-04-30
tags: [aider, provider, integration, relay, async, coder, tier-b, litellm]
related: [KB-2026-021, KB-2026-022, KB-2026-026, KB-2026-027, KB-2026-028]
---

# Aider as a Relay Provider: Integration Analysis

## Purpose

Determine how to wrap aider's `Coder` as a `BaseProvider` subclass so relay can use
any litellm-supported model (GPT-4o, Gemini, local Ollama) as a provider — not only
the two agentic CLIs (Claude Code, Codex).

---

## Coder API Facts (aider/coders/base_coder.py)

### Factory

```python
from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput

io = InputOutput(pretty=False, yes=True)
model = Model("gpt-4o-mini")                # any litellm model string
coder = Coder.create(main_model=model, io=io)
```

`Coder.create()` is the factory classmethod. Minimum required: `main_model`, `io`.
Selects the appropriate `Coder` subclass by `edit_format` (default: `EditBlockCoder`,
which uses SEARCH/REPLACE diffs). 13 subclasses available.

API keys are **not required at construction time** — only when `run()` is called. Keys
are read from environment variables at inference time via litellm.

### run() — the integration entry point

```python
result: str = coder.run(with_message="your task here", preproc=True)
# Returns self.partial_response_content — the complete assistant response
```

When `with_message` is provided:
- Sends the message to the model
- Applies file edits (reads/writes files in the working directory)
- Auto-commits changes if `auto_commits=True` (default)
- Runs up to 3 reflection rounds if linting catches errors
- **Returns** `self.partial_response_content` (the full assistant response text)
- Does **not** re-enter the interactive input loop

### Critical constraint: fully synchronous

```
Zero async/await in base_coder.py.
```

`run()`, `run_one()`, `send_message()`, `send()` are all blocking synchronous calls.
This is the primary integration challenge — relay's `run_turn()` is an `AsyncIterator`.

### auto_commits behaviour

```python
coder = Coder.create(main_model=model, io=io, auto_commits=True)  # default
```

aider auto-commits file edits after each `run()` call. This is the desired behaviour
for autonomous relay — it means git captures each aider turn as a commit, which MTARP
session state can reference. Set `auto_commits=False` only if relay will manage commits
itself (not recommended — aider's commit handling is more robust).

### Session state

aider maintains `coder.done_messages` (chat history) between `run()` calls on the same
`Coder` instance. This is the in-process equivalent of Claude Code's `session_id` or
Codex's `thread_id`. **The `Coder` instance must be preserved across turns** for
conversational continuity — it cannot be recreated per turn.

### Exhaustion / rate-limit signal

aider does not surface a structured `RateLimitEvent`. When a rate limit is hit,
litellm raises an exception that propagates through `send_message()`. The exception
type depends on the provider (OpenAI: `openai.RateLimitError`, Anthropic:
`anthropic.RateLimitError`). These need to be caught in `AiderProvider.run_turn()`.

No pre-exhaustion warning (`approaching_limit`) is available via aider/litellm.

---

## AiderProvider Design

### Sync-to-async bridge

`asyncio.to_thread()` runs the blocking `coder.run()` in a thread pool without
blocking the event loop:

```python
import asyncio
from collections.abc import AsyncIterator
from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput
from aider.providers.base import BaseProvider, ProviderEvent


class AiderProvider(BaseProvider):
    tier = "completion_api"

    def __init__(self, model: str, fnames: list[str] | None = None, **coder_kwargs):
        self._model_name = model
        self._fnames = fnames or []
        self._coder_kwargs = coder_kwargs
        self._coder: Coder | None = None

    def _get_coder(self) -> Coder:
        if self._coder is None:
            io = InputOutput(pretty=False, yes=True)
            model = Model(self._model_name)
            self._coder = Coder.create(
                main_model=model,
                io=io,
                fnames=self._fnames,
                auto_commits=True,
                **self._coder_kwargs,
            )
        return self._coder

    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]:
        coder = self._get_coder()
        try:
            response = await asyncio.to_thread(coder.run, with_message=prompt)
            yield ProviderEvent(type="text", content=response or "")
            yield ProviderEvent(type="done", session_id=None)
        except Exception as e:
            if _is_rate_limit(e):
                yield ProviderEvent(type="exhausted")
            else:
                yield ProviderEvent(type="error", content=str(e))

    @property
    def current_session_id(self) -> str | None:
        return None  # aider has no external session ID


def _is_rate_limit(exc: Exception) -> bool:
    name = type(exc).__name__
    return "RateLimit" in name or "rate_limit" in str(exc).lower()
```

### Tier classification

`AiderProvider.tier = "completion_api"` — aider reads/writes files itself via its
edit format (SEARCH/REPLACE), but it uses a stateless API call model (no persistent
subprocess session). For MTARP handoff context delivery, treat it as Tier B:
the relay should inject file contents into the handoff prompt, not just a git ref,
since aider does not have the same file-system awareness as Claude Code CLI.

**Exception:** if the target model supports tool use and aider is configured with
`ContextCoder` or `ArchitectCoder`, it can pull files autonomously — closer to Tier A.
Default `EditBlockCoder` is Tier B.

### No streaming to relay

`coder.run()` blocks until complete. Relay receives the full response as one `text`
event rather than a token stream. For the terminal UX this means no live output during
the aider turn — a spinner or "aider working..." message is appropriate.

Streaming from litellm to aider's internal `partial_response_content` accumulator
is still active (controlled by `coder.stream=True`) — the relay just doesn't see
the intermediate tokens. Could be addressed by sharing aider's `io` output stream,
but that's a Phase 2 concern.

---

## Use Cases in aider-relay

### Primary: unlimited overnight fallback

When Claude Code and Codex are both exhausted (daily limits hit), relay falls back to
`AiderProvider(model="ollama/deepseek-coder-v2")` — a local model with no usage limits.
The session continues autonomously overnight.

```python
providers = [
    ("claude", ClaudeCodeProvider()),
    ("codex", CodexProvider()),
    ("aider-local", AiderProvider("ollama/deepseek-coder-v2")),  # no limit
]
```

### Secondary: cheap judge panel

`AiderProvider(model="gpt-4o-mini")` or `AiderProvider(model="claude-haiku-4-5-20251001")`
used for the pre-handoff judge panel step (KB-2026-024): assess prior agent's output
before the incoming provider starts. Fast, cheap, no file edits needed (set
`auto_commits=False` for judge role).

### Not recommended: as primary coding provider

For complex agentic coding tasks, Claude Code CLI and Codex CLI outperform aider wrapping
a completion API. The CLIs have persistent tool call loops, better file context awareness,
and native git integration. Use `AiderProvider` as fallback, not primary.

---

## Open Questions Before Implementation

1. **Does `Model("gpt-4o-mini")` raise at construction if no API key is set?**
   Or only at inference time? If at construction, `AiderProvider.__init__` must defer
   `Model()` creation to first `run_turn()` call.

2. **Does `asyncio.to_thread(coder.run, with_message=prompt)` cause problems if
   aider's internal state is mutated in the thread while the event loop runs?**
   `Coder` is not thread-safe (mutable state: `done_messages`, `partial_response_content`).
   Safe if only one `run_turn()` is active at a time — which the relay's sequential
   execution model guarantees.

3. **What exception types does litellm raise for rate limits across different providers?**
   `_is_rate_limit()` above uses a name-match heuristic. Should enumerate the actual
   exception classes from litellm's exception mapping.

4. **Does aider's `io.yes=True` suppress all confirmation prompts?**
   Some aider operations (large file writes, shell commands) prompt the user for
   confirmation. `yes=True` should bypass these — but verify for the `bypassPermissions`
   equivalent in aider's model.

---

## Summary

| Concern | Resolution |
|---|---|
| Sync/async mismatch | `asyncio.to_thread(coder.run, with_message=...)` |
| Session continuity | Preserve `Coder` instance across turns (lazy init) |
| Auto-commits | Keep `auto_commits=True` — matches relay's git-first model |
| Rate limit detection | Catch exceptions, match on class name |
| Tier classification | `completion_api` (Tier B) for default `EditBlockCoder` |
| No streaming to relay | Single `text` event per turn; terminal shows spinner |
| Overnight fallback | `AiderProvider("ollama/deepseek-coder-v2")` — no limits |
