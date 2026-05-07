# Aider Setup — Local Model Coding Agent

Run a local AI coding agent (Qwen 3.5 35B-A3B) with access to your Claude Code skills, memory, and operating protocol.

## Prerequisites

- [Ollama](https://ollama.com) installed
- Qwen 3.5 35B-A3B model: `ollama pull qwen3.5:35b-a3b`
- Python 3.10+
- 64GB+ RAM recommended (128GB for full performance)

## Install

```bash
pip install aider-chat
```

## Configure

### 1. Create `.aider-context/` (gitignored — your local files stay local)

```bash
mkdir -p .aider-context
ln -sf ~/.claude .aider-context/.claude
```

This symlinks your local Claude config so the model can access your skills, memory, and hooks. Nothing is copied. Nothing is committed.

### 2. Create `.aider.conf.yml`

```yaml
model: ollama/qwen3.5:35b-a3b

read:
  - .aider-context/system-prompt.md
  - CLAUDE.md

map-tokens: 4096
no-show-model-warnings: true
no-auto-commits: true
```

### 3. Write your system prompt

Create `.aider-context/system-prompt.md` with instructions for how the model should behave. This is your system prompt — write it however you want.

### 4. Create `.aiderignore`

```
*
!gptcoach2/**
!ixcoach-api/**
!ixcoach-landing/**
!CLAUDE.md
!.claude/**
!.claude/skills/**
!portfolio/**
!shared-modules/**
!shared-tools/**

# Exclude build artifacts
**/node_modules/**
**/.next/**
**/dist/**
**/build/**
**/*.db
**/.git/**
**/pnpm-lock.yaml
**/package-lock.json
**/*.log
.claude/worktrees/**
.claude/logs/**
```

## Run

```bash
# Terminal UI
aider

# Browser UI
aider --browser
```

## Skills Access

Your Claude Code skills are accessible via the symlink at `.aider-context/.claude/skills/`. The model can read any skill file during conversation. Skills are never copied into the repo — they stay on your machine.

## Important

- `.aider-context/` is gitignored — it contains symlinks to YOUR local files
- `.aider.conf.yml` is gitignored — it may contain local paths
- `.aiderignore` is gitignored — customize for your needs
- **NEVER commit `.aider-context/` contents** — they point to private local files
