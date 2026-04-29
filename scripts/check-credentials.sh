#!/usr/bin/env bash
# Checks that credential directories exist on the host before devcontainer launch.
# Run this on the HOST before 'task dc:up'.
set -euo pipefail

CLAUDE_DIR="$HOME/.claude"
CODEX_DIR="$HOME/.codex"
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
