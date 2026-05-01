---
id: KB-2026-027
type: integration-spec
status: active
created: 2026-04-30
updated: 2026-04-30
tags: [aider, gitrepo, linter, integration, relay, git-context, stopping-conditions]
related: [KB-2026-021, KB-2026-026]
---

# Aider GitRepo and Linter: Integration Analysis for aider-relay

## Purpose

Evaluate whether aider's `GitRepo` and `Linter` classes are worth adopting in relay
to replace raw subprocess git calls and to implement autonomous stopping conditions.

---

## GitRepo

### Constructor (aider/repo.py:62-77)

```python
GitRepo(
    io,                                       # REQUIRED — InputOutput instance
    fnames,                                   # REQUIRED — list of files to track
    git_dname,                                # REQUIRED — path to git root
    aider_ignore_file=None,
    models=None,                              # for commit message generation
    attribute_author=True,
    attribute_committer=True,
    attribute_commit_message_author=False,
    attribute_commit_message_committer=False,
    commit_prompt=None,
    subtree_only=False,
    git_commit_verify=True,
    attribute_co_authored_by=False,
)
```

**Uses GitPython** (`import git`). Not subprocess-based.

### Methods relay needs

| Method | Signature | Returns | Replaces in relay |
|---|---|---|---|
| `get_head_commit_sha` | `(short=False)` | `str` (full or 7-char SHA) | `subprocess(["git", "rev-parse", "HEAD"])` in session.py |
| `diff_commits` | `(pretty, from_commit, to_commit)` | `str` (unified diff) | The `git diff <diff_since>..HEAD` in handoff_prompt |
| `get_diffs` | `()` | `str` (unified diff of working tree) | `subprocess(["git", "diff", "HEAD"])` in git_context() |
| `get_tracked_files` | `()` | `list[str]` filenames | Used to populate `files_in_scope` in Phase 2 session fields |
| `commit` | `(fnames, context, message, aider_edits, coder)` | `tuple(sha, msg)` or `None` | Not currently called by relay |

**Key:** `diff_commits(pretty, from_commit, to_commit)` is exactly what MTARP needs — takes
`session.git_diff_since` and `session.git_head` and returns the diff string for handoff context.

### The `io` coupling

GitRepo requires an `InputOutput` instance. The minimal construction for programmatic use:

```python
from aider.io import InputOutput
io = InputOutput(pretty=False, yes=True)
```

This is not expensive — no prompt_toolkit session is created if `pretty=False`.

### Verdict

**Worth adopting for relay.** `diff_commits()` and `get_head_commit_sha()` replace fragile
subprocess calls and handle edge cases (detached HEAD, merge commits, etc.) that the current
relay implementation does not. The `io` coupling is a two-line overhead, not a blocker.

**Immediate integration targets:**
- `session.py MTARPSession.create()` → replace `subprocess(["git", "rev-parse", ...])` with `GitRepo.get_head_commit_sha()`
- `relay_loop.py git_context()` → replace `subprocess(["git", "diff", ...])` with `GitRepo.get_diffs()`
- `relay_loop.py handoff_prompt()` → use `GitRepo.diff_commits(diff_since, head)` for MTARP-anchored diff

---

## Linter

### Constructor (aider/linter.py:22-29)

```python
Linter(encoding="utf-8", root=None)
```

Minimal — no external dependencies at init time.

### lint() return

Returns `str` (formatted markdown with error context) or `None` if no errors found.
Internally uses `LintResult(text: str, lines: list)` dataclass.

### Supported languages

**Python only by default.** `self.languages = dict(python=self.py_lint)`.
Uses flake8 if available; falls back to tree-sitter syntax check.

No built-in support for: YAML, TOML, Java, JavaScript, TypeScript, Shell, Go.

### No test runner

Linter has a generic `run_cmd()` method but no concept of running `task test` or
`task ci` and parsing pass/fail. It's a file-level lint tool, not a project-level
CI integration.

### Verdict for aider-relay

**Not worth adopting as the autonomous stopping condition mechanism.**

Reasons:
1. Python-only — polyglot-devcontainers is Java, Node, Python, Shell. Linter covers ~25% of files.
2. No test runner — the meaningful stopping condition for polyglot-devcontainers is `task test` or `task ci` passing, not file-level linting.
3. What it does (Python flake8) is already covered by the pre-commit hooks that run on every commit.

**Stopping condition implementation** should instead use:
- Git commit detection: after each provider turn, check if new commits landed (compare HEAD SHA before/after)
- `task test` invocation: run `subprocess(["task", "test"])` in the repo root, check return code
- `task ci` as the "full integration point" check

This is simpler and works for any language stack.

---

## Summary

| Component | Adopt? | What for |
|---|---|---|
| `GitRepo.diff_commits()` | ✅ Yes | MTARP handoff diff (diff_since..head) |
| `GitRepo.get_head_commit_sha()` | ✅ Yes | session.py git state capture |
| `GitRepo.get_diffs()` | ✅ Yes | git_context() in relay_loop |
| `GitRepo.get_tracked_files()` | ✅ Yes | Phase 2 `files_in_scope` |
| `Linter` | ❌ No | Python-only, no test runner, not useful for polyglot |
| Stopping condition | task subprocess | `task test` / commit count / wall-clock time |

## Integration cost

- Add `from aider.io import InputOutput` and `from aider.repo import GitRepo` to relay
- Create a shared `GitRepo` instance once in `relay()` and pass it to helpers
- `io` dependency: `InputOutput(pretty=False, yes=True)` — no interactive terminal spawned
- GitPython is already in aider's dependency tree (already installed in the venv)
