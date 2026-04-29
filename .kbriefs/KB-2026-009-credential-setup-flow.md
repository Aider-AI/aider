---
id: KB-2026-009
type: design-space
status: draft
created: 2026-04-28
updated: 2026-04-28
tags: [credentials, auth, claude-code, codex, devcontainer, setup-flow, oauth]
related: [KB-2026-001, KB-2026-006, KB-2026-008]
---

# Credential Setup Flow Design Space

## Context

Both Claude Code and Codex CLIs require authentication before use. Inside a devcontainer the standard browser-OAuth interactive flow is unavailable or awkward. aider-relay needs a credential setup flow that works for first-time users across: host-direct use, devcontainer use, and CI/automated use.

## Known Auth Mechanisms (per provider)

### Claude Code

| Method | Mechanism | Container-safe? | Notes |
|--------|-----------|-----------------|-------|
| Interactive OAuth | `claude auth login` → browser | No | Requires browser |
| Long-lived token | `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` env var | **Yes** | 1-year token, generated on host |
| API key | `ANTHROPIC_API_KEY` env var | **Yes** | Anthropic Console key, not Pro sub |
| Mounted credentials | Mount `~/.claude/` from host | **Yes** | Inherits host OAuth session |
| Credential storage | `~/.claude/.credentials.json` (mode 0600) | Via mount | Host file |

**Recommended for devcontainer:** `CLAUDE_CODE_OAUTH_TOKEN` env var, generated once via `claude setup-token` on the host.

### Codex

| Method | Mechanism | Container-safe? | Notes |
|--------|-----------|-----------------|-------|
| Interactive OAuth | `codex login` → browser | No | Requires browser |
| Device-code OAuth | `codex login` (device code, beta) | **Yes** | Terminal-only flow |
| API key | `OPENAI_API_KEY` or `CODEX_API_KEY` env var | **Yes** | OpenAI API key (metered, not Plus) |
| Mounted credentials | Mount `~/.codex/` from host | **Yes** | Inherits host OAuth session |
| Credential storage | `~/.codex/auth.json` | Via mount | Host file, tokens expire ~hourly, auto-refresh |

**Recommended for devcontainer:** Mount `~/.codex/` read-write from host OR `OPENAI_API_KEY` if using API key mode.

**Important distinction:** Codex with ChatGPT Plus OAuth uses `~/.codex/auth.json` with auto-refreshing tokens. Because tokens expire hourly, mounting the file read-write is necessary (the CLI writes refreshed tokens back). A static env var does not work for Plus OAuth.

## Design Space Options

### Option 1: Pure Environment Variables

Both providers get static tokens via env vars in devcontainer `containerEnv`.

```json
"containerEnv": {
  "CLAUDE_CODE_OAUTH_TOKEN": "${localEnv:CLAUDE_CODE_OAUTH_TOKEN}",
  "OPENAI_API_KEY": "${localEnv:OPENAI_API_KEY}"
}
```

Setup flow:
1. User runs `claude setup-token` on host → copies token to shell profile
2. User sets `OPENAI_API_KEY` in shell profile

- ✅ Simple, no file mounts
- ✅ Works for API key users
- ❌ Codex Plus OAuth: token expires hourly, no auto-refresh possible
- ❌ Requires manual token generation step
- ❌ `OPENAI_API_KEY` = metered API, not Plus subscription

### Option 2: Credential Directory Mounts

Mount provider credential directories from host into container.

```json
"mounts": [
  "source=${localEnv:HOME}/.claude,target=/home/vscode/.claude,type=bind",
  "source=${localEnv:HOME}/.codex,target=/home/vscode/.codex,type=bind"
]
```

- ✅ Inherits host auth state, including Plus OAuth
- ✅ Auto-refresh works (container can write updated tokens)
- ✅ No manual token generation step
- ⚠️ Container writes session data back to host dirs (acceptable — desired for session continuity)
- ❌ Fails if dirs don't exist on host (need guard in setup script)
- ❌ Shared sessions between host and container (could interleave session state)

### Option 3: Hybrid — Mount + Env Var Fallback

Try mounts first; fall back to env vars if dirs don't exist. Setup script detects which mode applies.

```bash
# scripts/setup-credentials.sh
if [ -d "$HOME/.claude" ]; then
  echo "Claude: credential dir found — will mount"
else
  echo "Claude: no credentials. Run 'claude auth login' on host first, or set CLAUDE_CODE_OAUTH_TOKEN"
  exit 1
fi
```

- ✅ Most flexible
- ✅ Works for both Plus OAuth and API key users
- ✅ Clear error messages guide the user
- Medium complexity

### Option 4: `aider-relay setup` Command

A first-run CLI command that:
1. Detects missing credentials
2. Guides user through the correct auth flow for their environment
3. Writes a `.env.devcontainer` file (git-ignored) with env vars
4. Devcontainer sources this file on creation

- ✅ Best UX — automated, guided
- ❌ Requires building the setup command before providers can be used
- Use as Phase 2 after basic credential mounting works

## Recommended Approach (Phase 1)

**Option 2 (credential directory mounts)** as the primary path, with:
- Guard script that checks dirs exist before launch
- Instructions in README for first-time setup (log in on host first)
- `containerEnv` kept as fallback for CI/API-key users

## devcontainer.json Changes Required

```json
{
  "mounts": [
    "source=${localEnv:USERPROFILE}\\.claude,target=/home/vscode/.claude,type=bind",
    "source=${localEnv:USERPROFILE}\\.codex,target=/home/vscode/.codex,type=bind"
  ]
}
```

Note: Windows paths use `USERPROFILE` not `HOME` in devcontainer variable expansion.

## Open Questions

1. Does mounting `~/.codex/auth.json` (read-write) from a Podman container on Windows/WSL work reliably with path translation?
2. Does `claude` inside the container respect `CLAUDE_CODE_OAUTH_TOKEN` without `~/.claude/` being present?
3. What happens if Claude Code CLI inside the container tries to write session state to `~/.claude/` when it's mounted from the host — does it conflict with the host's running Claude Code instance?

## Experiment to Run (Host-safe, no quota)

```bash
# On host — check what's in credential dirs without reading secrets
ls -la ~/.claude/
ls -la ~/.codex/
# Then try: does CLAUDE_CODE_OAUTH_TOKEN work without mounting ~/.claude/?
CLAUDE_CODE_OAUTH_TOKEN=$(claude setup-token 2>/dev/null) claude auth status
```

## Applicability

- ✅ Required before any devcontainer-based experiments can run
- ✅ Drives the devcontainer.json mounts design
- ✅ Informs the `aider-relay setup` command design (Phase 2)
