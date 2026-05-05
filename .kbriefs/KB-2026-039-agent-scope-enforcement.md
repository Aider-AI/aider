# KB-2026-039: Agent Scope Enforcement — Zero-Trust Policy for Relay Runs

**Status:** Implemented (two-tier model) — 2026-05-03  
**Date:** 2026-05-03  
**Context:** Observed during polyglot-devcontainers OpenRewrite run — agent installed tools instead of using existing repo infrastructure

## Problem

During the OpenRewrite relay run, the agent began installing tools rather than
using the repo's established approach (devcontainer + Gradle wrapper). Prompt
instructions alone were not sufficient to prevent this — the agent reasoned its
way into believing tool installation was necessary to make progress.

"Don't install tools" is a recoverable prompt instruction; "tools are not
available to install" is a hard constraint. The gap is between policy stated in
text and policy enforced by the environment.

## Root Cause

The relay currently has no mechanism to restrict what system-level actions an
agent can take. The agent runs inside a devcontainer with network access, a
package manager, and sudo-equivalent permissions. A sufficiently determined agent
(or a confused one) can install packages, modify system state, or diverge from
the intended task boundary.

Prompts set intention. They do not enforce it.

## Scope Taxonomy

Three categories of agent action relevant to relay tasks:

| Category | Examples | Policy |
|---|---|---|
| **Expected** | Read/write files in scope, run `./gradlew`, run `task` commands | Always allowed |
| **Reviewable** | Git commit, run tests outside task spec | Allowed but logged |
| **Blocked** | `apt install`, `npm install -g`, `pip install` outside venv, `curl \| bash` | Never allowed |

## Options

**A. Sandbox via container image (zero capability by default)**

Build a relay-task container image with only the tools the task needs pre-installed.
No package manager write access. No network access except to defined endpoints.
Agent cannot install because the capability does not exist.

Strong guarantee. Requires per-task or per-project image specification. High setup cost.

**B. Allow-list shell commands in Claude Code settings**

Claude Code's `settings.json` supports `allowedTools` and per-command allow-lists
for Bash. A relay-task `.claude/settings.json` can specify exactly which shell
commands are permitted. Commands outside the list require explicit user approval
(which the relay never provides, so they block).

Low setup cost. Enforced by the Claude Code harness, not by prompt. Only covers
Claude Code as provider; Codex would need equivalent mechanism.

**C. Filesystem-level restrictions (read-only mounts)**

Mount the system package directories read-only inside the container. Agent can
read but cannot modify system state. Task working directory remains read-write.

Stronger than prompts. Does not cover network-based installs (pip, npm from network).

**D. Relay-side action classifier (post-hoc)**

After each agent turn, the relay parses the diff and shell history for out-of-scope
actions. If found, it injects a correction prompt and rolls back the action.
Complex to implement reliably; still reactive rather than preventive.

## Implemented: Two-Tier Trust Model

The long command allow-list approach was rejected. Enumerating every safe command
is fragile (the agent finds gaps) and grows indefinitely as tools are added to the image.

**Implemented instead: single gateway pattern.**

```
┌─────────────────────────────────────────────────────────────────┐
│  HOST / RELAY CONTAINER                                         │
│                                                                 │
│  Tier H-1 — always allowed (pure reads, no side effects):       │
│    File ops: Read / Write / Edit / Glob / Grep / LS             │
│    Git read: git status / log / diff / stash list               │
│    (needed for MTARP session.json: files_in_scope, summary)     │
│                                                                 │
│  Tier H-2 — container exec gateway:                             │
│    devpod exec <name> -- <anything>                             │
│    devcontainer exec --workspace-folder <path> -- <anything>    │
│    devpod up / devcontainer up   (lifecycle only)               │
│                                                                 │
│  Everything else: absent from allowedTools → Claude Code blocks │
└──────────────────────────┬──────────────────────────────────────┘
                           │ exec gateway
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  TARGET DEVCONTAINER  (polyglot-devcontainers image)            │
│                                                                 │
│  Unrestricted — Docker is the sandbox:                          │
│    ./gradlew build / test / rewrite:dry-run                     │
│    task lint / test / ci                                        │
│    git commit / push  (credentials + git config live here)      │
│    npm install, apt-get install  (contained, not host)          │
└─────────────────────────────────────────────────────────────────┘
```

**Why this is better than the enumeration approach:**
- One meta-rule replaces an ever-growing list
- Container image is the trust boundary — adding a new tool to the image requires
  no settings.json update
- Git writes (commit, push) route through the container where credentials live,
  directly resolving KB-2026-038's credential gap

**Files implementing this:**

| File | Role |
|---|---|
| `templates/claude-settings.json` | Two-tier allowedTools; copy to `.claude/settings.json` in target repo |
| `scripts/relay.sh` | `--container NAME` / `--workspace-folder PATH`; copies settings, starts container, passes exec-prefix |
| `scripts/relay_loop.py` | `--exec-prefix CMD`; prepends gateway instruction to initial task |
| `aider/providers/claude_code.py` | Changed `bypassPermissions` → `acceptEdits` so settings.json actually applies |

**Key: `bypassPermissions` change**

`acceptEdits` (implemented) auto-accepts file edits but respects `allowedTools` for
Bash commands. `bypassPermissions` bypassed everything — including the allow-list.
Without this change, the settings.json would have no effect on shell commands.

**Usage:**

```bash
# devpod (auto-starts container)
bash scripts/relay.sh \
  --repo /workspaces/polyglot-devcontainers \
  --container polyglot-devcontainers \
  --autonomous --max-turns 30 --turn-timeout 120 \
  --task-file .aider-relay/TASK.md

# devcontainer CLI (container must be running)
bash scripts/relay.sh \
  --repo /workspaces/polyglot-devcontainers \
  --workspace-folder /workspaces/polyglot-devcontainers \
  --autonomous --max-turns 30 \
  --task-file .aider-relay/TASK.md
```

## Open Question

`devpod exec *` allows exec into any devpod container, not just the target.
If multiple containers are present this is a weak boundary. Future hardening:
pass the exact container name into a more specific allow pattern. Low priority
for single-project relay runs.
