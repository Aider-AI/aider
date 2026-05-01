---
id: KB-2026-030
type: implementation-plan
status: active
created: 2026-04-30
updated: 2026-04-30
tags: [aider, integration, plan, gitrepo, repomap, provider, relay, autonomous]
related: [KB-2026-027, KB-2026-028, KB-2026-029, KB-2026-021, KB-2026-024]
---

# Aider Integration Plan for aider-relay

## Summary of What to Integrate and Why

Three integration surfaces identified across KB-2026-027/028/029:

| Surface | What it gives relay | When |
|---|---|---|
| `GitRepo` | Replaces fragile subprocess git calls; enables `diff_commits()` for MTARP handoff | Phase 1 (now — low risk, high correctness) |
| `AiderProvider` | Any litellm model as a relay provider; unlimited local fallback via Ollama | Phase 1 (autonomous relay MVP) |
| `RepoMap` | Semantic code map as handoff context instead of raw diff | Phase 2 (after autonomous relay is working) |

---

## Phase 1 Integration: GitRepo + AiderProvider

These two unlock the MVP. Do them together — they share the same `io` and `Model` objects.

### Step 1 — Replace subprocess git calls with GitRepo

**Files changed:** `aider/relay/session.py`, `scripts/relay_loop.py`

```python
# Shared setup (in relay() function or module level):
from aider.io import InputOutput
from aider.repo import GitRepo

_io = InputOutput(pretty=False, yes=True)
_git = GitRepo(io=_io, fnames=[], git_dname=str(Path.cwd()))
```

| Current (subprocess) | Replacement (GitRepo) |
|---|---|
| `subprocess(["git", "rev-parse", "HEAD"])` | `_git.get_head_commit_sha()` |
| `subprocess(["git", "rev-parse", "--abbrev-ref", "HEAD"])` | `_git.repo.active_branch.name` |
| `subprocess(["git", "diff", "HEAD"])` | `_git.get_diffs()` |
| `subprocess(["git", "log", "--oneline", "-10"])` | `_git.repo.git.log("--oneline", "-10")` |

For MTARP handoff diff (diff_since → head):
```python
diff = _git.diff_commits(
    pretty=False,
    from_commit=session.git_diff_since,
    to_commit=session.git_head,
)
```

**Risk:** Low. GitPython is already installed. `GitRepo` is stable and battle-tested.
Graceful fallback: keep subprocess calls as fallback if `GitRepo` init fails.

### Step 2 — Add AiderProvider

**File:** `aider/providers/aider_coder.py` (new)

Implementation as specified in KB-2026-029. Key decisions:

- Lazy `Coder` init: defer `Model()` and `Coder.create()` to first `run_turn()` so
  missing API keys fail at runtime, not at provider construction
- `auto_commits=True`: aider commits its own changes, relay reads the resulting git state
- `asyncio.to_thread()`: safe because relay's sequential execution model ensures only
  one `run_turn()` is active at a time
- `tier = "completion_api"`: relay injects file contents in handoff prompt (not git ref only)

**Resolve open questions before writing code:**

1. Test `Model("gpt-4o-mini")` construction with no API key set — does it raise?
2. Enumerate litellm rate-limit exception classes for `_is_rate_limit()`
3. Verify `InputOutput(pretty=False, yes=True)` suppresses all confirmation prompts

### Step 3 — Add autonomous mode to relay_loop.py

**File:** `scripts/relay_loop.py`

```
--autonomous          skip user input between turns; loop provider until done or limit
--max-turns N         stop after N total turns across all providers (default: unlimited)
--task-file PATH      read initial task from a markdown file
--resume              read existing .aider-relay/session.json and continue from last state
```

Autonomous loop (replaces the `input("You: ")` block):
```python
if autonomous:
    prompt = CONTINUATION_PROMPT
else:
    prompt = input("You: ").strip()
```

Stopping conditions (checked after each successful turn):
1. `--max-turns` reached → write session.json, exit
2. New commit landed (HEAD SHA changed) AND task appears complete → pause/exit
3. Both providers exhausted → write session.json, print reset times, exit

### Step 4 — Provider cycling (drop the 2-exhaustion ceiling)

Replace `exhausted_count >= 2` with provider-specific exhaustion tracking:

```python
exhausted: set[str] = set()   # providers exhausted this run

if result == "exhausted":
    exhausted.add(active)
    other = fallback if active == primary else primary
    if other in exhausted:
        print("[RELAY] All providers exhausted. Session saved.")
        break
    active = other
```

When a third provider (AiderProvider/Ollama) is in the list, this naturally extends
to 3+ providers before stopping.

---

## Phase 2 Integration: RepoMap

Do this after the autonomous relay is working end-to-end.

### Step 5 — RepoMap handoff context

**File:** `scripts/relay_loop.py` `handoff_prompt()` function

```python
from aider.repomap import RepoMap
from aider.models import Model

def _build_repomap_context(session: MTARPSession, git_repo: GitRepo) -> str:
    model = Model("claude-haiku-4-5-20251001")   # token counting only
    io = InputOutput(pretty=False, yes=True)
    repo_map = RepoMap(
        map_tokens=2048,
        root=str(Path.cwd()),
        main_model=model,
        io=io,
    )
    all_files = git_repo.get_tracked_files()
    changed = _files_changed_in_session(session, git_repo)
    return repo_map.get_repo_map(chat_files=changed, other_files=all_files) or ""
```

Injected into `handoff_prompt()` as a new section:
```
## Repository map (files touched this session)
<repomap output>
```

### Step 6 — Phase 2 session fields

Add to `MTARPSession` and `session.json`:
- `files_in_scope`: list of files changed during the session (from `git diff --name-only`)
- `session_summary`: LLM-generated summary of what was done (using `AiderProvider`'s
  model or a cheap model via litellm directly)

---

## Dependency Map

```
AiderProvider  →  needs  →  Model, InputOutput, Coder
GitRepo        →  needs  →  InputOutput, GitPython (already installed)
RepoMap        →  needs  →  Model, InputOutput, tree-sitter (already installed)
```

`InputOutput(pretty=False, yes=True)` is shared across all three.
`Model` is shared between `AiderProvider` and `RepoMap` if same model string is used.

Create one shared `_io` and one shared `_model` at the top of the relay session.
Pass them down — don't recreate per turn.

---

## What This Enables for the Polyglot-Devcontainers MVP

| Capability | Enabled by |
|---|---|
| Autonomous coding without user input | Step 3 (--autonomous) |
| Clean provider switching on exhaustion | Step 4 (cycling) |
| Overnight local fallback (Ollama) | Step 2 (AiderProvider) |
| Robust git state capture | Step 1 (GitRepo) |
| Rich handoff context for incoming provider | Step 5 (RepoMap, Phase 2) |
| Resumable sessions across days | Step 3 (--resume) |

---

## Implementation Order

```
Step 1: GitRepo replacement          — 2–3 hours, low risk, immediate correctness gain
Step 2: AiderProvider                — 3–4 hours, resolves 4 open questions first
Step 3: Autonomous mode              — 2–3 hours, unlocks the MVP
Step 4: Provider cycling             — 1 hour, 5-line change
─── MVP complete: can run polyglot-devcontainers ──────────────────────────────────────
Step 5: RepoMap handoff              — 2–3 hours, improves handoff quality
Step 6: Phase 2 session fields       — 3–4 hours, structured progress tracking
```

Total to MVP: ~8–11 hours of implementation.
Total to full Phase 2: additional 5–7 hours.
