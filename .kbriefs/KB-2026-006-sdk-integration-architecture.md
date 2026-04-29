---
id: KB-2026-006
type: standard
status: draft
created: 2026-04-27
updated: 2026-04-28
tags: [sdk, claude-agent-sdk, subprocess, architecture, provider-interface]
related: [KB-2026-001, KB-2026-003, KB-2026-007, KB-2026-010]
---

# SDK Integration Architecture Standard

## Context & Problem Statement

Both Claude Code and Codex have official Python SDKs. We need a common provider interface that wraps both so the orchestration layer can call either without knowing which is active.

## Standard/Pattern Description

### Core Principles

1. Both providers expose an identical async interface to the orchestrator
2. Neither provider knows about the other
3. Session IDs are managed by the provider, not the orchestrator
4. The orchestrator injects context at the start of each new session

### Provider Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class ProviderEvent:
    type: str          # "text", "tool_use", "exhausted", "error", "done"
    content: str = ""
    reset_at: str | None = None   # human-readable reset time if exhausted
    session_id: str | None = None

class BaseProvider(ABC):
    @abstractmethod
    async def start_session(self, context: "RelayContext") -> str:
        """Start a new session with injected context. Returns session_id."""

    @abstractmethod
    async def resume_session(self, session_id: str, prompt: str) -> AsyncIterator[ProviderEvent]:
        """Send a turn to an existing session, yielding events."""

    @abstractmethod
    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]:
        """Run a single turn in the current session, yielding events."""

    @property
    @abstractmethod
    def current_session_id(self) -> str | None:
        """Return the active session ID for context snapshotting."""
```

### Claude Code Provider Implementation Sketch

Uses `RateLimitEvent` from the SDK directly — no string parsing needed (see KB-2026-002).

```python
from claude_agent_sdk import query, ClaudeAgentOptions, RateLimitEvent
from aider_relay.providers.base import BaseProvider, ProviderEvent
from datetime import datetime, timezone

class ClaudeCodeProvider(BaseProvider):
    def __init__(self):
        self._session_id: str | None = None

    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]:
        async for msg in query(prompt=prompt, resume_session=self._session_id):
            if hasattr(msg, "session_id"):
                self._session_id = msg.session_id
            if isinstance(msg, RateLimitEvent):
                info = msg.rate_limit_info
                if info.status == "rejected":
                    reset_at = (
                        datetime.fromtimestamp(info.resets_at, tz=timezone.utc).isoformat()
                        if info.resets_at else None
                    )
                    yield ProviderEvent(type="exhausted", reset_at=reset_at)
                    return
                # "allowed_warning" — caller may want to snapshot context proactively
            elif hasattr(msg, "result"):
                yield ProviderEvent(type="text", content=msg.result)
            elif hasattr(msg, "error"):
                yield ProviderEvent(type="error", content=str(msg.error))
        yield ProviderEvent(type="done", session_id=self._session_id)
```

### Codex Provider Implementation Sketch

`codex-app-server` does not exist on PyPI. Codex integration is subprocess-based via `codex exec --json` (see KB-2026-010 for the full validated interface).

```python
import asyncio
import json
from collections.abc import AsyncIterator
from aider_relay.providers.base import BaseProvider, ProviderEvent

class CodexProvider(BaseProvider):
    def __init__(self):
        self._thread_id: str | None = None

    async def run_turn(self, prompt: str) -> AsyncIterator[ProviderEvent]:
        if self._thread_id is None:
            cmd = ["codex", "exec", "--json", "--sandbox", "workspace-write", prompt]
        else:
            cmd = ["codex", "exec", "resume", self._thread_id, prompt,
                   "--json", "--sandbox", "workspace-write"]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async for raw in proc.stdout:
            event = json.loads(raw)
            match event["type"]:
                case "thread.started":
                    self._thread_id = event["thread_id"]
                case "item.completed":
                    item = event.get("item", {})
                    if item.get("type") == "agent_message":
                        yield ProviderEvent(type="text", content=item.get("text", ""))
                case "turn.failed":
                    err = event.get("error", {})
                    if err.get("code") == "rate_limit_exceeded":
                        yield ProviderEvent(type="exhausted")
                    else:
                        yield ProviderEvent(type="error", content=str(err))
                case "turn.completed":
                    yield ProviderEvent(type="done", session_id=self._thread_id)

        await proc.wait()

    @property
    def current_session_id(self) -> str | None:
        return self._thread_id
```

## Key Rules

- Providers must emit `ProviderEvent(type="exhausted")` when usage window is exhausted
- Providers must NOT retry internally on exhaustion (the orchestrator decides what to do)
- Providers must persist `session_id` / `thread_id` across turns for session continuity
- Context injection happens in `start_session()`, not in `run_turn()`

## Rationale & Benefits

- Clean separation: orchestrator never imports SDK-specific code
- Testable: providers can be mocked in unit tests
- Extensible: new providers (Gemini CLI, etc.) implement `BaseProvider`
- Failure isolation: one provider crash doesn't affect the other

## Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "claude-agent-sdk",
    "codex-app-server",
]
```

Both CLIs must also be installed in the environment:
```bash
npm install -g @anthropic-ai/claude-code @openai/codex
```

## Experiment Required

- Validate that `claude_agent_sdk` is installable from PyPI and the interface matches the sketch above
- Validate that `codex-app-server` is installable from PyPI and thread management works as documented
- Both need authentication to be set up in the devcontainer

## Applicability

- ✅ All provider adapter code in `aider_relay/providers/`
- ❌ Does not apply to context relay logic — see KB-2026-007
