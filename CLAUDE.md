# aider-relay

Hard fork of aider. Orchestrates Claude Code and Codex CLI as relay providers,
switching on usage exhaustion via MTARP (KB-2026-021/026).

## Branch workflow

**Never work directly on `main`.** Always create a feature branch before starting
any implementation work:

```bash
git checkout -b feat/<short-name>   # new feature
git checkout -b fix/<short-name>    # bug fix
git checkout -b docs/<short-name>   # KB briefs, docs only
```

Open a PR to `main` when the work is ready. Merge via GitHub, not locally.

## Task commands (run inside devcontainer)

```bash
task init        # bootstrap venv (first time only)
task lint        # isort + black + flake8 + codespell
task test        # pytest tests/
task scan        # security scan
task ci          # full pipeline (lint + test + scan)
```

## Commit and push workflow

**Commits require the devcontainer** — the pre-commit hook uses a venv built for
the `/workspaces/` path. Committing on the host fails.

```bash
# Start devcontainer if not running
task dc:up

# Commit via devcontainer
task dc:exec -- git commit -m "type: description"

# Push from host (no hook needed)
git push
```

## Architecture

- `scripts/relay_loop.py` — relay state machine, provider cycling, MTARP session write
- `aider/providers/` — BaseProvider, ClaudeCodeProvider, CodexProvider, AiderProvider
- `aider/relay/session.py` — MTARPSession (session.json schema)
- `tests/` — pytest, no real CLI calls; mock providers via `tests/helpers.py`

## KBPD methodology

Knowledge gaps are recorded as K-Briefs in `.kbriefs/`. Create a K-Brief before
building anything non-trivial. Index is in `memory/MEMORY.md`.

## Non-obvious constraints

- `InputOutput(pretty=False, yes=True)` auto-answers all aider prompts except
  `explicit_yes_required=True` (shell command execution — intentionally blocked).
- `Model("...")` never raises at construction without an API key; errors surface
  at first `run_turn()` call.
- RepoMap uses Tree-sitter locally — no API calls during `get_repo_map()`.
