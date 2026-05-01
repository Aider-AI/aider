---
id: KB-2026-028
type: integration-spec
status: active
created: 2026-04-30
updated: 2026-04-30
tags: [aider, repomap, integration, relay, handoff-context, tree-sitter]
related: [KB-2026-021, KB-2026-026, KB-2026-027]
---

# Aider RepoMap: Integration Analysis for aider-relay

## Purpose

Evaluate whether aider's `RepoMap` can replace `git diff HEAD` as handoff context in the
MTARP session envelope, producing a richer semantic briefing for the incoming provider.

---

## API Facts (aider/repomap.py)

### Constructor

```python
RepoMap(
    map_tokens=1024,         # max tokens for the map output
    root=None,               # directory root (defaults to os.getcwd())
    main_model=None,         # EFFECTIVELY REQUIRED — used for token_count()
    io=None,                 # EFFECTIVELY REQUIRED — used for read_text()
    repo_content_prefix=None,
    verbose=False,
    max_context_window=None,
    map_mul_no_files=8,
    refresh="auto",
)
```

All parameters have defaults, but **`io` and `main_model` are effectively required**:
- `io` is called unconditionally as `self.io.read_text(fname)` in the file parsing path
- `main_model` is called unconditionally as `self.main_model.token_count(text)` during map generation
- Both will raise `AttributeError` if `None` is passed and `get_repo_map()` is called

### get_repo_map()

```python
def get_repo_map(
    self,
    chat_files,          # list[str] — files "in chat" (prioritised in map)
    other_files,         # list[str] — all other repo files to consider
    mentioned_fnames=None,
    mentioned_idents=None,
    force_refresh=False,
) -> str | None:
```

Returns a **formatted string** (the repo map) or `None` if:
- `max_map_tokens <= 0`
- `other_files` is empty
- No parseable content found

The string output is a ranked list of file definitions (functions, classes, symbols)
formatted for LLM consumption. Token budget is controlled by `map_tokens`.

---

## Dependencies

All already in aider's dependency tree (and thus in the relay venv):
- `tree-sitter==0.25.2` (Python ≥ 3.10)
- `tree-sitter-language-pack==0.13.0`
- `grep-ast==0.9.0` — language detection and grammar lookup
- `diskcache==5.6.3` — tag cache

**Non-code files (YAML, TOML, Shell):** handled gracefully. `filename_to_lang()` returns
`None` for unrecognised extensions; those files are silently skipped in the map. No crash.

**Git not required.** RepoMap uses filesystem scanning, not git metadata. Works on any directory.

---

## Minimal Programmatic Construction

```python
from aider.io import InputOutput
from aider.models import Model
from aider.repomap import RepoMap

io = InputOutput(pretty=False, yes=True)          # no interactive terminal
model = Model("claude-haiku-4-5-20251001")        # cheap model, token counting only
repo_map = RepoMap(
    map_tokens=2048,
    root="/path/to/repo",
    main_model=model,
    io=io,
)
context = repo_map.get_repo_map(
    chat_files=changed_files,    # files the outgoing agent worked on
    other_files=all_repo_files,  # everything else for ranking
)
```

**`model` is used only for token counting** — it does not make LLM API calls during
`get_repo_map()`. A haiku-class model is fine and doesn't require credits if only
`token_count()` is called. Verify: `model.token_count()` uses litellm's local counter,
not an API call.

---

## Integration Points for aider-relay

### 1. Handoff prompt enrichment

Current handoff context: `git diff HEAD` truncated at 8,000 chars — raw, noisy.

With RepoMap: structured list of definitions in files that changed during the session.
Token budget can be set to 2,048–4,096 (well within any provider's context window).

**In relay_loop.py `handoff_prompt()`:**
```python
repo_map = RepoMap(map_tokens=2048, root=repo_root, main_model=model, io=io)
all_files = git_repo.get_tracked_files()
map_context = repo_map.get_repo_map(
    chat_files=changed_files_this_session,
    other_files=all_files,
)
```

### 2. session.json Phase 2 field: `files_in_scope`

`GitRepo.get_tracked_files()` (KB-2026-027) produces the full file list. The files that
changed during the session (`git diff --name-only diff_since..head`) are the
`files_in_scope` candidates. RepoMap ranking can prioritise these in the handoff.

---

## Known Constraint: Model Dependency

`main_model` must be a model object with a `token_count(text: str) -> int` method.
Relay currently has no `Model` instance (it drives CLI tools, not the litellm layer).

**Resolution options:**

**Option A — Instantiate a cheap Model for token counting only (recommended):**
```python
from aider.models import Model
_token_model = Model("claude-haiku-4-5-20251001")
```
No API call is made unless the model is used for inference. Token counting is local
via litellm's built-in counter. Cost: zero.

**Option B — Implement a duck-typed stub:**
```python
class _TokenCounter:
    def token_count(self, text: str) -> int:
        return len(text) // 4  # rough approximation
```
Avoids the litellm dependency entirely. Less accurate but no model config required.
Adequate if the token budget doesn't need to be precise.

**Recommendation:** Option A for correctness; Option B as a fallback when no model
config is available (e.g., running relay without any API key configured).

---

## Verdict

**Worth adopting for Phase 2 handoff enrichment.** Not for Phase 1 (minimum viable
autonomous relay) — Phase 1 can keep the current `git diff` approach. Add RepoMap in
the same phase as Phase 2 session fields (`files_in_scope`, `session_summary`).

| Use | When | Value |
|---|---|---|
| Handoff context enrichment | Phase 2 | High — replaces diff noise with semantic map |
| files_in_scope population | Phase 2 | Medium — structured file list for incoming agent |
| Phase 1 autonomous relay | Not needed | git diff is sufficient for MVP |

**Blocking question before implementation:** does `Model.token_count()` require an active
API key at instantiation, or only at inference time? If instantiation requires a key,
Option B (stub) is needed for environments without credentials configured.
