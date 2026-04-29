---
id: KB-2026-003
type: design-space
status: validated
created: 2026-04-27
updated: 2026-04-27
tags: [architecture, sdk, integration-path, claude-code, codex]
related: [KB-2026-001, KB-2026-006, KB-2026-007]
---

# CLI Provider Adapter Architecture Design Space

## Context

Initial hypothesis was a local HTTP proxy or subprocess adapter. Research confirmed both CLIs have **official Python SDKs** that manage subprocess lifecycle. This K-Brief records the validated architecture direction.

## Options Evaluated

### Option A: Local OpenAI-Compatible HTTP Proxy
**Status: ELIMINATED**

Rationale: Both SDKs make this unnecessary. The SDKs handle subprocess management, JSON-RPC, streaming, and session resumption. Building a proxy would duplicate what the SDKs already provide.

### Option B: Raw Subprocess (stdin/stdout)
**Status: ELIMINATED**

Rationale: Both SDKs wrap subprocess management correctly. Raw subprocess would require re-implementing retry, streaming, error parsing, and session persistence that the SDKs provide for free.

### Option C: litellm CustomLLM Provider
**Status: PARTIALLY APPLICABLE**

The CLIs are not completion APIs — they are agentic coding runtimes. litellm's CustomLLM interface expects a completion-style call; mapping agentic sessions to that interface is an impedance mismatch.

Use litellm only if a thin shim is needed to bridge the relay's orchestration layer to a completion-like interface.

### Option D (VALIDATED): Official Python SDKs

**Claude Code:** `claude-agent-sdk`
```python
from claude_agent_sdk import query, ClaudeAgentOptions
async for message in query(prompt=..., options=...):
    process(message)
```

**Codex:** `codex-app-server`
```python
from codex_app_server import AsyncCodex
async with AsyncCodex() as codex:
    thread = await codex.thread_start()
    result = await thread.run(prompt)
```

- **Reliability**: High — official, maintained by providers
- **Latency**: Minimal overhead — SDKs manage subprocess efficiently
- **Complexity**: Low — clean Python APIs, no HTTP server to build
- **Streaming**: Yes — both SDKs support async streaming events
- **Session management**: Built-in — IDs, resume, fork
- **Maintenance**: Provider-maintained

## Validated Architecture

```
aider-relay orchestrator
        │
        ├── ClaudeCodeProvider (claude-agent-sdk)
        │       ├── session_id management
        │       ├── exhaustion detection
        │       └── context snapshot on switch
        │
        └── CodexProvider (codex-app-server)
                ├── thread_id management
                ├── exhaustion detection
                └── context injection on resume
```

The orchestrator maintains the **higher-level context relay** (KB-2026-007) independently of both providers, so neither provider needs to know about the other.

## New Architectural Constraint Revealed

The SDKs are designed for agentic coding tasks, not for intercepting mid-conversation and passing context. The "higher-level context" problem (KB-2026-007) is the dominant design challenge — the SDK integration itself is straightforward.

## Applicability

- ✅ Determines the dependency set (both SDKs required in pyproject.toml)
- ✅ Determines devcontainer tooling (Node.js required for CLI binaries)
- ❌ Does not resolve the context relay design — see KB-2026-007
