# KB-2026-043: aider-relay Distribution Modes

**Status:** Partially implemented  
**Date:** 2026-05-03  
**Context:** User needs to invoke aider-relay from Windows host directly, not via devcontainer

## Two target modes

### Mode 1: Windows host (current primary target)

```
Windows host
├── Claude Code CLI (npm, in PATH)
├── Codex CLI (npm, in PATH)
├── Podman Desktop / devpod / devcontainer CLI
├── Python 3.12+ with aider-relay installed
└── relay.ps1 (or aider-relay CLI) → relay_loop → Claude Code agent
                                          └── podman exec <container> → all execution
```

The relay orchestrator and Claude Code agent run natively on Windows.
All build/test/git-write commands route through the container exec gateway.
The host trust boundary (`templates/claude-settings.json`) is enforced by Claude Code's
`allowedTools` — only file ops, git reads, and the exec gateway are permitted on the host.

**Invocation:**
```powershell
.\scripts\relay.ps1 `
    --repo C:\dev\polyglot-devcontainers `
    --podman-container polyglot-devcontainers `
    --autonomous --max-turns 30 --turn-timeout 120 `
    --task-file .aider-relay\TASK.md
```

Or if installed (`uv pip install -e .` from repo root):
```powershell
aider-relay --exec-prefix "podman exec polyglot-devcontainers" `
    --autonomous --max-turns 30 --task-file .aider-relay\TASK.md
```

### Mode 2: Headless relay container (future)

```
Relay container (minimal image: Python + aider-relay + Claude Code + Codex)
└── relay_loop → Claude Code agent
                    └── podman exec / devpod exec → target devcontainer → all execution
```

The relay itself runs in a container with no GUI. Triggered by:
- A CI/CD pipeline (GitHub Actions, scheduled task)
- A long-running daemon on the host that watches for TASK.md changes
- A Task command: `task relay:run`

The relay container needs:
- Access to the Docker/Podman socket (to exec into other containers)
- Or SSH access to the devpod container
- `GH_TOKEN` / SSH key for git operations inside the target container
- Mount of the target workspace (or network access for git clone)

## Current packaging state

| Component | State |
|---|---|
| `aider/relay/loop.py` | Main relay logic; importable as package |
| `aider/relay/session.py` | MTARP session; importable as package |
| `pyproject.toml` entry point | `aider-relay = "aider.relay.loop:main"` ✓ fixed |
| `scripts/relay_loop.py` | Compatibility shim re-exporting from `aider.relay.loop` |
| `scripts/relay.ps1` | Windows host wrapper; handles gateway setup |
| `scripts/relay.sh` | Linux/macOS wrapper; handles gateway setup |

## Install path (Mode 1, from source)

```powershell
# In the aider-relay repo root on Windows:
pip install uv          # if not already present
uv venv --python 3.12
uv pip install -e .
# aider-relay is now in .venv\Scripts\ and on PATH if venv is activated
```

Or without activating the venv:
```powershell
uv run aider-relay --help
```

## What's needed for Mode 2 (headless container)

1. **Relay container image** — Dockerfile: Python 3.12 + `uv pip install aider-relay` +
   `npm install -g @anthropic-ai/claude-code @openai/codex`. Keep it minimal.
2. **Socket / exec access** — The relay container must be able to reach the target container.
   Options: Podman socket bind mount, devpod SSH, or network exec proxy.
3. **Credentials** — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GH_TOKEN` injected as env vars
   (not baked into image). Use container secrets or CI env vars.
4. **Trigger mechanism** — Taskfile target (`task relay:headless`), GitHub Actions workflow,
   or a file-watcher that fires when `.aider-relay/TASK.md` appears in a branch.

## Relation to existing work

- KB-2026-039: Host trust boundary (allowedTools, exec gateway) — implemented
- KB-2026-038: Git credentials inside container — Mode 1 routes git writes through container,
  solving the credential gap at the architecture level
- `relay:polyglot` in Taskfile.yml — the temporary workaround this replaces
