---
parent: Architecture Overview
nav_order: 140
---

# Git Integration and Auto‑Commit

Git operations are handled by `aider/repo.py`.  `GitRepo` wraps GitPython to stage files, commit them, and generate diffs.  The coder passes `edited` filenames to `auto_commit()` which formats a commit message (sometimes via the LLM) and calls `GitRepo.commit()`.

```python
def commit(self, fnames=None, context=None, message=None, aider_edits=False, coder=None):
    # Build commit message and set attribution
    self.repo.index.add(fnames)
    self.repo.index.commit(message, author=..., committer=...)
```

If `--auto-commit` is enabled, every successful edit cycle results in a commit.  The commit hash is reported back in the chat so the user can inspect or revert.  Manual `/commit` is available to checkpoint changes at any time.

The repo map also relies on Git to list tracked files and to ignore paths described in `.gitignore` and `.aiderignore`.

