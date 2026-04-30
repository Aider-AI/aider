#!/usr/bin/env bash
# Checks that credential directories exist on the host before devcontainer launch.
# Run this on the HOST before 'task dc:up'.
set -euo pipefail

# Resolve the Windows host home directory across WSL, Git Bash, and native Linux.
if grep -qi microsoft /proc/version 2>/dev/null; then
  # WSL: translate Windows USERPROFILE into a /mnt/c/... path
  if command -v wslvar &>/dev/null; then
    WIN_HOME=$(wslvar USERPROFILE 2>/dev/null)
  else
    WIN_HOME=$(cmd.exe /C "echo %USERPROFILE%" 2>/dev/null | tr -d '\r\n')
  fi
  HOST_HOME=$(wslpath "$WIN_HOME" 2>/dev/null || echo "$HOME")
elif [ -n "${USERPROFILE:-}" ] && command -v cygpath &>/dev/null; then
  # Git Bash / MSYS2
  HOST_HOME=$(cygpath -u "$USERPROFILE")
else
  HOST_HOME="$HOME"
fi

CLAUDE_DIR="$HOST_HOME/.claude"
CODEX_DIR="$HOST_HOME/.codex"
MISSING=0

echo "=== aider-relay credential check ==="
echo ""

# Claude Code
if [ -d "$CLAUDE_DIR" ]; then
  echo "✓ Claude: $CLAUDE_DIR found"
else
  echo "✗ Claude: $CLAUDE_DIR not found"
  echo "  Run on host: claude auth login"
  MISSING=1
fi

# Codex
if [ -d "$CODEX_DIR" ]; then
  echo "✓ Codex:  $CODEX_DIR found"
else
  echo "✗ Codex:  $CODEX_DIR not found"
  echo "  Run on host: codex login"
  MISSING=1
fi

echo ""

if [ "$MISSING" -eq 1 ]; then
  echo "One or more credential directories are missing."
  echo "Log in on the host machine first, then re-run 'task dc:up'."
  exit 1
fi

echo "All credential directories present. Devcontainer launch should work."
