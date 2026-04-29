---
id: KB-2026-008
type: standard
status: validated
created: 2026-04-27
updated: 2026-04-27
tags: [devcontainer, environment, python-node, polyglot, development-workflow]
related: [KB-2026-001, KB-2026-006]
---

# Devcontainer Development Environment Standard

## Context & Problem Statement

aider-relay requires both Python (the codebase is a Python fork of aider) and Node.js (both Claude Code CLI and Codex CLI are npm packages). Development must be reproducible across machines and produce consistent results.

## Standard: Use polyglot-devcontainers Python+Node Image

### Image

```
ghcr.io/senanayake/polyglot-devcontainers-python-node:v0.0.27
```

This image provides:
- Python 3.12 + `uv` package manager
- Node.js 22 + npm (required for `@anthropic-ai/claude-code` and `@openai/codex`)
- `task` runner (implements the standard task contract)
- `ruff` linter, `pytest`, `pip-audit`, `gitleaks`
- `gh` GitHub CLI, `git`, `pre-commit`

### Why Python+Node (not Python-only)

Both CLIs are npm packages installed globally:
```bash
npm install -g @anthropic-ai/claude-code
npm install -g @openai/codex
```

These are not Python packages — they require Node. Python-only images cannot run the CLIs.

### devcontainer.json

```json
{
  "name": "aider-relay",
  "image": "ghcr.io/senanayake/polyglot-devcontainers-python-node:v0.0.27",
  "postCreateCommand": "task init && pre-commit install",
  "customizations": {
    "vscode": {
      "settings": {
        "editor.formatOnSave": true,
        "python.defaultInterpreterPath": "/workspaces/aider-relay/.venv/bin/python",
        "python.testing.pytestEnabled": true,
        "python.testing.pytestArgs": ["tests"],
        "python.analysis.typeCheckingMode": "basic"
      },
      "extensions": [
        "ms-python.python",
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker"
      ]
    }
  },
  "remoteUser": "vscode"
}
```

### Task Contract

```yaml
# Taskfile.yml
tasks:
  init:
    desc: Bootstrap dev environment
    cmds:
      - uv sync --frozen --extra dev
      - npm install -g @anthropic-ai/claude-code @openai/codex

  lint:
    desc: Run code quality checks
    cmds:
      - uv run ruff check .
      - uv run ruff format --check .

  test:
    desc: Run test suite
    cmds:
      - uv run pytest tests/

  scan:
    desc: Run security checks
    cmds:
      - uv run pip-audit

  ci:
    desc: Full validation pipeline
    cmds:
      - task: lint
      - task: test
      - task: scan
```

## Authentication Constraint (Known Limitation)

The CLIs require interactive authentication that cannot be automated in devcontainer setup:

- Claude Code: `claude auth login` (browser OAuth) or set `CLAUDE_CODE_OAUTH_TOKEN`
- Codex: `codex login` (browser or device-code OAuth) or set `OPENAI_API_KEY`

**Standard:** Use environment variables via `~/.claude/settings.json` or devcontainer `containerEnv` to inject tokens. Never store tokens in the repo.

Recommended `.devcontainer/devcontainer.json` addition:
```json
{
  "containerEnv": {
    "CLAUDE_CODE_OAUTH_TOKEN": "${localEnv:CLAUDE_CODE_OAUTH_TOKEN}",
    "OPENAI_API_KEY": "${localEnv:OPENAI_API_KEY}"
  }
}
```

This reads from the host machine's environment variables, keeping credentials out of the container image and repo.

## Applicability

- ✅ All development of aider-relay
- ✅ CI/CD pipelines (use environment variables for auth)
- ❌ Production deployment (different packaging concerns)
