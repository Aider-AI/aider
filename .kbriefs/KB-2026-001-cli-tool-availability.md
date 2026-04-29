---
id: KB-2026-001
type: design-space
status: validated
created: 2026-04-27
updated: 2026-04-27
tags: [cli-provider, claude-code, codex, integration-path, sdk]
related: [KB-2026-002, KB-2026-003, KB-2026-006]
---

# CLI Tool Availability and API Exposure

## Context

aider-relay routes model calls through official consumer subscription CLIs rather than direct API keys. This K-Brief records what tools are confirmed available and how they expose their interfaces.

## Confirmed Tools (validated 2026-04-27)

### Claude Pro → Claude Code CLI

- **Package:** `@anthropic-ai/claude-code` (npm global)
- **Python SDK:** `claude-agent-sdk` (`pip install claude-agent-sdk`)
- **Non-interactive mode:** `claude -p "prompt" --output-format json|stream-json`
- **Session management:** sessions stored on disk, resumable via `--resume <session_id>`
- **Local HTTP server:** NO native HTTP endpoint. Communication is stdin/stdout only for subprocess use, OR via the Python SDK which manages the subprocess.
- **Official:** Yes — Anthropic-maintained

**Python SDK interface:**
```python
from claude_agent_sdk import query, ClaudeAgentOptions
async for message in query(
    prompt="...",
    options=ClaudeAgentOptions(allowed_tools=["Read","Edit","Bash"]),
):
    ...
```

**Session resumption:**
```python
from claude_agent_sdk import list_sessions, get_session_messages
sessions = list_sessions(directory="/path/to/project", limit=10)
messages = get_session_messages(sessions[0].session_id, limit=50)
```

**Authentication:** OAuth via `claude auth login` (interactive), or `CLAUDE_CODE_OAUTH_TOKEN` env var for non-interactive use. `claude setup-token` generates a 1-year OAuth token.

### ChatGPT Plus → OpenAI Codex CLI

- **Package:** `@openai/codex` (npm global)
- **Python SDK:** `codex-app-server` (`pip install codex-app-server`, Python 3.10+)
- **Non-interactive mode:** `codex exec "task" --json` (JSONL to stdout, progress to stderr)
- **Session management:** sessions in `~/.codex/sessions/`, resumable via `codex resume <session_id>`
- **Local server:** YES — `codex app-server --listen stdio://` or `--listen ws://127.0.0.1:4500` exposes JSON-RPC 2.0
- **Official:** Yes — OpenAI-maintained

**Python SDK interface:**
```python
from codex_app_server import AsyncCodex
async with AsyncCodex() as codex:
    thread = await codex.thread_start(model="gpt-5.4")
    result = await thread.run("Your prompt here")
```

**Authentication:** `codex login` (OAuth, ChatGPT Plus/Pro/Business) or `OPENAI_API_KEY` / `CODEX_API_KEY` env var for API-key mode.

## Critical Architectural Insight

Both CLIs are **agentic coding assistants** — they read files, run bash commands, make edits. They are NOT simple chat completion APIs. This fundamentally changes the integration approach compared to the initial litellm-proxy hypothesis:

- They manage their own view of the codebase
- They have their own session/context state
- Switching between them requires **higher-level context handoff**, not just message array transfer

See KB-2026-006 for the SDK integration architecture and KB-2026-007 for the context relay design.

## Dominated Options (eliminated)

- Community web proxies (claude-to-api, chatgpt-web-wrappers) — ToS risk, fragile
- ChatGPT Plus API access — does not exist; Plus ≠ API access

## Applicability

- ✅ All provider adapter implementation decisions
- ✅ Devcontainer must include Node.js (both CLIs are npm packages)
