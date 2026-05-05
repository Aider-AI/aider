# KB-2026-038: Worktree .git Path Unreachable from Linux Container

**Status:** Implemented (Option B+E)  
**Date:** 2026-05-02  
**Context:** Observed during first relay run against polyglot-devcontainers feat/java-openrewrite

## Problem

When a git worktree is created on a Windows host (`C:\dev\polyglot-openrewrite`), its
`.git` file contains the Windows path to the parent repo's worktree metadata:

```
gitdir: C:/dev/polyglot-devcontainers/.git/worktrees/polyglot-openrewrite
```

When that worktree directory is bind-mounted into the Linux devcontainer
(`/workspaces/polyglot-devcontainers`), git inside the container reads the `.git` file
and tries to resolve `C:/dev/polyglot-devcontainers/.git/...` — a path that does not
exist in the Linux filesystem. Every git operation fails silently or with path errors.

The agent spent ~60% of its turns (~15 device flow attempts + multiple GIT_DIR override
experiments) trying to recover from this at runtime. None succeeded.

## Root Cause

Git worktrees store an absolute host path in their `.git` file at creation time.
The path is host-native (Windows here). There is no runtime mechanism to remap it
inside a container without modifying the file or providing environment variable overrides
that correctly reconstruct the path — which requires knowing the Linux translation of the
Windows path, which varies by container runtime and mount configuration.

## Options

**A. Rewrite the `.git` file before mounting (pre-flight step)**

Before `task relay:polyglot` runs, a script rewrites the worktree `.git` file to use
the Linux-resolvable path:
```
gitdir: /workspaces/polyglot-devcontainers-main/.git/worktrees/polyglot-openrewrite
```
This requires also mounting the main repo's `.git` directory at a known path.
Fragile: must be re-run whenever the worktree is recreated.

**B. Mount main repo `.git` alongside the worktree**

Add a second mount to `devcontainer.json`:
```json
"source=C:\\dev\\polyglot-devcontainers\\.git,target=/workspaces/polyglot-devcontainers-git,type=bind"
```
Then set the `GIT_DIR` and `GIT_WORK_TREE` environment variables in `relay.sh` before
running the agent. The agent sees a working git repo without any `.git` file remapping.
More robust; survives worktree recreation.

**C. Use a full clone inside the container instead of a worktree mount**

`relay.sh` clones the target repo's feature branch into a temp directory inside the
container at startup. The agent commits and pushes directly. No worktree path issues.
Downside: clone time, network dependency, and any changes the agent makes are not
immediately visible on the host filesystem.

**D. Commit from the host, not from inside the container**

The agent writes files but does not commit. A post-run step on the Windows host
stages and commits from the worktree where git works natively. Simplest for now;
breaks the "agent completes the task end-to-end" goal.

**E. Pass `GIT_DIR` / `GIT_WORK_TREE` via `relay.sh`**

`relay.sh` accepts `--git-dir` and `--work-tree` args and exports them as env vars
before spawning the agent. The agent inherits a working git context without needing
to resolve the `.git` file. Requires knowing the Linux path of the parent `.git` at
relay invocation time.

## Recommendation

**Short term:** Option D — the host handles commits after the agent finishes.
Agents already cannot push without credentials (see related gap); host commit + push
is already the manual step. Document this in the TASK.md template as expected behaviour.

**Medium term:** Option B + E combined — mount the parent `.git`, pass `GIT_DIR`
and `GIT_WORK_TREE` via `relay.sh`. This gives agents full git capability without
worktree path remapping, and cleanly separates "where the files are" from "where git
metadata lives".

**Do not pursue:** Option A (fragile) or Option C (loses host filesystem visibility
during the run, which is valuable for monitoring).

## Related Gap

The container also has no GitHub credentials. Even with git working, the agent cannot
push without a `GH_TOKEN` or SSH key passed into the container. This must be addressed
in `devcontainer.json` (add `GH_TOKEN` to `containerEnv` from `localEnv`) alongside
whichever git path option is chosen. These are two separate problems that both need
fixing before agents can commit and push end-to-end.

## Implementation

Option B+E implemented:

- `devcontainer.json`: mounts `C:\dev\polyglot-devcontainers\.git` → `/workspaces/polyglot-devcontainers-main-git`; forwards `GH_TOKEN` from host env.
- `relay.sh`: new `--git-dir` / `--work-tree` args export `GIT_DIR` and `GIT_WORK_TREE` before spawning the relay. Also detects broken worktree `.git` files at startup and warns with fix instructions. Env vars are propagated via `CONTAINER_ENV_ARGS` for podman exec modes.
- `Taskfile relay:polyglot`: passes `--git-dir /workspaces/polyglot-devcontainers-main-git/worktrees/polyglot-openrewrite --work-tree /workspaces/polyglot-devcontainers`.

Setting `GIT_DIR` bypasses `.git` file discovery entirely; git reads `commondir` (relative path `../../..`) inside the worktree admin dir to locate the main `.git`, which resolves correctly against the mounted path.
