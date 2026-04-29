---
id: KB-2026-012
type: design-space
status: validated
created: 2026-04-28
updated: 2026-04-28
tags: [packaging, windows, installation, pip, pipx, uv, git-url, nodejs, npm]
related: [KB-2026-011, KB-2026-013, KB-2026-014]
---

# Windows Installation from GitHub Fork: Design Space

## Context

aider-relay is a Python CLI that also requires Node.js 22 and two npm packages (`@anthropic-ai/claude-code`, `@openai/codex`). Target users are developers on Windows host machines. The package is not (initially) on PyPI — it must be installable directly from GitHub.

This brief maps the full design space for getting both the Python package and the npm dependencies onto a Windows user's machine.

## Problem Statement

No standard Python package manager (pip, pipx, uv) installs npm packages. The Python install step and the Node.js install step are fundamentally separate operations. Any installation strategy must address both halves.

## Design Space Dimensions

- **Install friction**: How many manual steps does the user need to run?
- **Isolation**: Does the tool environment stay isolated from system Python?
- **Node.js handling**: How is the npm dependency problem solved?
- **Windows compatibility**: Does this work without WSL?
- **Upgradability**: How does a user get a new version?

## Part 1: Python Package Installation Options

### Option A: `uv tool install git+https://...`

```powershell
uv tool install --python python3.12 --force `
  git+https://github.com/senanayake/aider-relay
```

How it works:
- uv resolves, downloads, and installs the package from the GitHub URL into an isolated tool environment.
- `--python python3.12` causes uv to auto-download CPython 3.12 from Astral's python-build-standalone if not already present. No separate Python installer needed.
- `--force` re-installs over any existing version.
- The `aider-relay` binary is placed in `%USERPROFILE%\.local\bin` (or equivalent uv bin dir) and added to PATH automatically.
- Branch/tag specifiers work: `git+https://github.com/senanayake/aider-relay@v0.1.0`

Strengths:
- Fully isolated environment (no system Python pollution).
- Automatic Python version management — user does not need Python pre-installed.
- Single command.
- Same mechanism that aider upstream uses in its official install scripts.
- uv is available as a standalone installer for Windows (no Python required to get uv).

Weaknesses:
- Requires `uv` to be installed first (one prerequisite step).
- git must be present for the `git+https://` clone (git for Windows is common but not universal).
- Does NOT install npm packages — see Part 2.

**Verdict: Preferred Python install method.**

### Option B: `pipx install git+https://...`

```powershell
pipx install git+https://github.com/senanayake/aider-relay --python python3.12
```

How it works:
- pipx creates an isolated venv, installs the package from the git URL, and exposes the entry point on PATH.
- `--python python3.12` selects the Python version (uses the Windows `py` launcher or a found interpreter; does NOT auto-download Python).
- `pipx inject <name> <extra-package>` can add more Python packages to an existing pipx env, but cannot run npm.

Strengths:
- Well-known tool, wide install base.
- Isolated environments.
- git URL support works (pip is the underlying installer).

Weaknesses:
- Does not auto-download Python. User must have Python 3.12 installed separately.
- Does NOT install npm packages.
- Less ergonomic than uv for this use case.

**Verdict: Viable fallback, but uv is strictly better here.**

### Option C: `pip install git+https://...` (inside a venv)

```powershell
python3.12 -m venv aider-relay-env
aider-relay-env\Scripts\activate
pip install git+https://github.com/senanayake/aider-relay
```

How it works:
- Standard pip + venv approach. Works reliably on Windows.
- git URL support is native to pip (`git+https://` scheme).
- User must manage PATH manually or always activate the venv.

Strengths:
- Zero extra tooling required beyond Python and git.
- Maximum compatibility.

Weaknesses:
- No automatic isolation of the entry point binary.
- User must have Python 3.12 installed.
- Manual venv lifecycle.
- Does NOT install npm packages.

**Verdict: Developer-suitable, not appropriate as a first-run user experience.**

### Option D: setuptools post-install hook (run npm from pip)

There is no official setuptools post-install hook that runs arbitrary shell commands after `pip install`. The `setup.py install` command existed historically but is deprecated. Attempts to run `subprocess.run(["npm", "install", "-g", ...])` from a custom `install` command class work only when the user invokes `python setup.py install` — which is itself deprecated and bypassed by pip's build isolation.

**Verdict: Eliminated. Pip does not support arbitrary post-install steps.**

## Part 2: Node.js Dependency Installation

The npm packages `@anthropic-ai/claude-code` and `@openai/codex` must be installed separately. Options:

### Option N1: Manual npm install (user-performed)

The installation guide instructs the user to run, after the Python install:

```powershell
npm install -g @anthropic-ai/claude-code @openai/codex
```

Requires: Node.js 22 on PATH. Users install Node from `https://nodejs.org` or via `winget install OpenJS.NodeJS.LTS`.

**Friction**: One extra step, but it is a one-time setup and well-understood by the developer audience.

### Option N2: aider-relay-install wrapper package

A thin `aider-relay-install` PyPI package (mirroring the `aider-install` pattern):

```python
# aider_relay_install/main.py
import subprocess, sys, uv, shutil

def install():
    uv_bin = uv.find_uv_bin()
    subprocess.check_call([
        uv_bin, "tool", "install", "--force", "--python", "python3.12",
        "git+https://github.com/senanayake/aider-relay"
    ])
    subprocess.check_call([uv_bin, "tool", "update-shell"])
    # Node.js check + npm install
    if shutil.which("npm") is None:
        print("ERROR: Node.js 22 must be installed first. See https://nodejs.org")
        sys.exit(1)
    subprocess.check_call(["npm", "install", "-g",
        "@anthropic-ai/claude-code", "@openai/codex"])
```

Published to PyPI as `aider-relay-install`. Install flow:

```powershell
# Step 1: Install Node.js 22 (winget or nodejs.org)
winget install OpenJS.NodeJS.LTS

# Step 2: Install and run the thin installer
pip install aider-relay-install
aider-relay-install
```

Strengths:
- Single-command feel after Node is present.
- Handles both Python and npm halves.
- Can validate Node version before proceeding.

Weaknesses:
- Requires publishing a second PyPI package.
- Still cannot automate Node.js installation itself (winget requires user consent).

### Option N3: PowerShell install script (mirroring install.ps1)

A hosted `https://aider-relay.example.com/install.ps1` that:
1. Checks for/installs uv.
2. Checks for Node.js 22 (warns or exits if absent).
3. Runs `uv tool install --python python3.12 git+https://github.com/senanayake/aider-relay`.
4. Runs `npm install -g @anthropic-ai/claude-code @openai/codex`.

```powershell
# User runs:
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/senanayake/aider-relay/main/scripts/install.ps1 | iex"
```

Strengths:
- Closest to zero-friction experience.
- Can provide clear error messages for missing Node.js.
- No PyPI publishing required.

Weaknesses:
- Node.js installation from a script requires admin rights or winget user consent — not fully automatable.
- Script hosting requires a stable URL.
- Scripts are harder to test.

## Recommended Strategy

**Two-step documented install** (lowest complexity to ship):

```powershell
# Step 1: Install Node.js 22 (one-time, skip if already installed)
winget install OpenJS.NodeJS.LTS

# Step 2: Install uv (one-time, skip if already installed)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Step 3: Install aider-relay
uv tool install --python python3.12 --force git+https://github.com/senanayake/aider-relay

# Step 4: Install npm CLI dependencies
npm install -g @anthropic-ai/claude-code @openai/codex
```

This matches the developer audience's expectations, requires no PyPI publishing, and maps directly to what aider upstream does for its own install flow.

**Upgrade path:**
```powershell
uv tool install --python python3.12 --force git+https://github.com/senanayake/aider-relay@main
npm install -g @anthropic-ai/claude-code @openai/codex  # re-run to update npm packages
```

## Design Space Map

| Option | Friction | Isolation | Node handling | Python auto-download | Notes |
|--------|----------|-----------|---------------|---------------------|-------|
| uv tool install (git URL) | Low | Excellent | Manual npm step | Yes | Preferred |
| pipx install (git URL) | Medium | Good | Manual npm step | No | Viable fallback |
| pip in venv | High | Manual | Manual npm step | No | Dev-only |
| Post-install hook (npm) | Eliminated | N/A | N/A | N/A | pip does not support |
| aider-relay-install pkg | Very Low | Excellent | Automated check | Yes | Best UX, needs PyPI |
| PowerShell install.ps1 | Very Low | Excellent | Guided | Yes | Best UX, no PyPI needed |

## Constraints

- Node.js cannot be installed by pip, pipx, or uv. This is a hard constraint. Any install story that omits this step is incomplete.
- `uv tool install` with `--python python3.12` will auto-download Python 3.12 using python-build-standalone if not found — this is a significant UX advantage on Windows.
- git for Windows must be present for `git+https://` cloning by any Python installer. Most developers already have it.

## Applicability

- Applies to: Windows host machine, developer audience
- Does not apply to: devcontainer setup (see KB-2026-008), Linux CI (different script)
