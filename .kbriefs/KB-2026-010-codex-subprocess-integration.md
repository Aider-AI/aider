---
id: KB-2026-010
type: standard
status: validated
created: 2026-04-28
updated: 2026-04-29
tags: [codex, subprocess, jsonl, session-management, integration-path, python]
related: [KB-2026-001, KB-2026-002, KB-2026-006]
---

# Codex CLI Subprocess Integration Standard

## Context & Problem Statement

KB-2026-001 documented `codex-app-server` as the Python SDK for Codex. That package **does not exist on PyPI**. This K-Brief records the validated integration path: subprocess adapter over `codex exec --json`.

## Validated Integration Path: subprocess + JSONL

The Codex CLI (`@openai/codex` npm) exposes a non-interactive mode that emits structured JSONL to stdout. This is the only Python-accessible integration path.

### Commands

**New session:**
```bash
codex exec --json "<prompt>"
```

**Resume session:**
```bash
codex exec resume <session_id> "<prompt>" --json
```

**Skip git repo requirement (useful in ephemeral environments):**
```bash
codex exec --json --skip-git-repo-check "<prompt>"
```

**Allow file writes (required for coding tasks):**
```bash
codex exec --json --sandbox workspace-write "<prompt>"
```

### JSONL Event Taxonomy (validated 2026-04-28, extended 2026-04-29)

A complete turn produces this event sequence on stdout:

```jsonl
{"type":"thread.started","thread_id":"019dd753-b1e4-7f21-add4-91c3727048ed"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"4"}}
{"type":"turn.completed","usage":{"input_tokens":9866,"cached_input_tokens":2432,"output_tokens":16,"reasoning_output_tokens":18}}
```

**`reasoning_output_tokens`** appears in `turn.completed` when the active model is a reasoning model (e.g. o4-mini). The field is absent for non-reasoning models. The `CodexProvider` must treat it as optional.

**Key events:**

| Event type | When | Key fields |
|---|---|---|
| `thread.started` | First event in any turn | `thread_id` — UUID, use for session resumption |
| `turn.started` | Start of agent processing | — |
| `item.completed` | Each agent output item | `item.type`, `item.text` (for `agent_message`) |
| `turn.completed` | End of turn | `usage.input_tokens`, `usage.cached_input_tokens`, `usage.output_tokens` |
| `turn.failed` | On error | `error.message`, `error.code` |

Additional `item.type` values expected for coding tasks (not yet captured): `tool_call`, `tool_result`, `code_change`.

### Session Resumption (validated 2026-04-28, confirmed in devcontainer 2026-04-29)

`codex exec resume <thread_id> "<prompt>" --json` correctly resumes the session. Validated: the resumed session retains conversational context (model answered a follow-up correctly without re-stating prior answer). The same `thread_id` is returned in `thread.started` on resumption.

**Token caching on resume**: `cached_input_tokens` jumped from 3,456 to 7,936 on the second turn — prior context is cached server-side, not in the local sqlite db.

**Session state is server-side.** The local `~/.codex/state_5.sqlite` is only a cache for the interactive UI. This means session resumption works correctly even when the local db write fails (see stderr error below).

### Stderr

Functional errors (e.g. "not inside a trusted directory") go to stderr and do not appear in the JSONL stream.

**Known benign stderr error in devcontainer (validated 2026-04-29):**
```
ERROR codex_core::session: failed to record rollout items: thread <id> not found
```
This appears after every successful call when `~/.codex/` is host-mounted into the container. The CLI fails to write the session to the local SQLite cache due to a file locking or schema conflict between host and container. **It does not affect call success or session resumption** — both work correctly because session state is held server-side. The `CodexProvider` subprocess adapter should log this error at DEBUG level and not treat it as a failure.

## CodexProvider Implementation

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
            cmd = ["codex", "exec", "resume", self._thread_id, prompt, "--json",
                   "--sandbox", "workspace-write"]

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

## Alternative: MCP Server Mode

`codex mcp-server` starts Codex as a stdio MCP server. This is an alternative integration path that exposes Codex as an MCP tool provider rather than a subprocess. Not explored further — the subprocess path above is sufficient for Phase 1 and avoids MCP protocol overhead.

## Requirements Impact

Remove `codex-app-server` from `requirements/requirements.in` — the package does not exist on PyPI. The Codex integration is entirely subprocess-based; no Python package is required beyond the stdlib `asyncio` + `json`.

The `@openai/codex` npm package must be installed in the environment (already in `Taskfile.yml` `init` task).

## Remaining Gaps

- **Exhaustion signal**: `turn.failed` with `error.code == "rate_limit_exceeded"` is the expected signal (per KB-2026-002), but whether a **subscription window** exhaustion (vs TPM) produces this same code, and whether any `retry_after` field is present, is not yet validated. Requires deliberately exhausting a ChatGPT Plus session.
- **Tool use events**: `item.type` values for file reads, shell commands, and edits during a coding task have not been observed. A coding task experiment is needed to capture the full event vocabulary.

## Applicability

- ✅ Replaces `codex-app-server` in all provider code
- ✅ Remove `codex-app-server` from `requirements.in`
- ✅ `CodexProvider` in `aider_relay/providers/codex.py`
- ✅ No pip dependency needed — pure subprocess
