---
id: KB-2026-014
type: tradeoff
status: validated
created: 2026-04-28
updated: 2026-04-28
tags: [packaging, pypi, publishing, distribution, github-releases, wheels, fork]
related: [KB-2026-011, KB-2026-012, KB-2026-013]
---

# Publishing Options for aider-relay

## Context

aider-relay must be installable by developers. The question is whether to publish to PyPI, distribute via GitHub Releases, rely on direct git URL installs, or some combination. This brief analyses the trade-offs, with specific attention to the constraints of a fork.

## Variables

### Variable 1: Install friction

How many steps and how much prior knowledge does a user need? Measured as number of commands and whether those commands require context (knowing a PyPI name vs. a GitHub URL).

### Variable 2: Maintenance burden

How much ongoing work does the publishing mechanism create? Measured as: number of extra CI steps, number of extra credentials/tokens to manage, risk of name conflicts.

### Variable 3: Discoverability

Can users find aider-relay without already knowing the GitHub URL? PyPI search is the primary discovery channel for Python tools.

### Variable 4: Fork legitimacy / legal clarity

Does the chosen publishing approach respect the upstream Apache 2.0 license and avoid confusion with the original? PyPI name conflicts, PyPI description ambiguity, and trademark concerns are real risks.

## Options

### Option 1: No PyPI — install from GitHub URL directly

Users install with:
```bash
uv tool install git+https://github.com/senanayake/aider-relay --python python3.12 --force
```

No package is published anywhere. The GitHub repo IS the distribution artifact.

Strengths:
- Zero maintenance burden. No PyPI account, no CI publish step, no token management.
- No name conflict with upstream `aider-chat`.
- Every commit on `main` is immediately installable — no release ceremony required.
- Appropriate for a project that is not yet stable.

Weaknesses:
- Higher install friction: users must know the GitHub URL.
- No version pinning via PyPI (must use `@tag` in the git URL for pinning).
- `uv pip compile` / `pip freeze` workflows cannot lock to a PyPI release.
- No discoverability via `pip search` or PyPI browsing.

**Assessment: Correct starting point for early-stage development. Adds zero overhead.**

### Option 2: PyPI under a new name (`aider-relay`)

Publish `aider-relay` to PyPI. Users install with:
```bash
pip install aider-relay
pipx install aider-relay
uv tool install aider-relay --python python3.12
```

Fork-specific considerations:
- **Can you publish a fork under a new name?** Yes. PyPI has no concept of "forks". Any package with a unique name can be published. The original `aider-chat` is Apache 2.0 licensed, which explicitly permits redistribution under a different name, provided the license is retained.
- **Name availability**: The name `aider-relay` is not currently registered on PyPI (as of 2026-04-28 based on research). Registration is first-come, first-served.
- **pyproject.toml change required**: `name = "aider-relay"` and entry point `aider-relay = "aider.main:main"` (or keep `aider` for drop-in compatibility, but that risks PATH conflicts if user also has upstream `aider-chat` installed).

Publishing workflow (GitHub Actions, Trusted Publishing):
```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/aider-relay
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # required for setuptools_scm
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Trusted Publishing eliminates the need for a stored PYPI_API_TOKEN secret. It uses OIDC from GitHub Actions, configured once on the PyPI project page.

Strengths:
- Standard install experience (`pip install aider-relay`).
- Version pinning is straightforward.
- Discoverability.

Weaknesses:
- Release ceremony: must tag + push, CI runs, PyPI publishes. Git URL install is always ahead of PyPI.
- setuptools_scm versioning requires `fetch-depth: 0` in CI.
- Ongoing maintenance: keep `name`, `description`, and `Homepage` URL accurate to avoid confusing users who expect the original aider.
- If upstream aider renames itself or publishes `aider-relay`, there could be confusion.

**Assessment: Appropriate once aider-relay is stable enough for versioned releases. Not needed immediately.**

### Option 3: GitHub Releases with pre-built wheels

Tag a release on GitHub and attach `.whl` files as release assets. Users install with:
```bash
pip install https://github.com/senanayake/aider-relay/releases/download/v0.1.0/aider_relay-0.1.0-py3-none-any.whl
```

Or with uv:
```bash
uv tool install https://github.com/senanayake/aider-relay/releases/download/v0.1.0/aider_relay-0.1.0-py3-none-any.whl --python python3.12
```

Building wheels in CI:
```yaml
- run: pip install build
- run: python -m build --wheel
- uses: softprops/action-gh-release@v2
  with:
    files: dist/*.whl
```

Strengths:
- Versioned, immutable artifacts.
- No PyPI account or ceremony.
- URL is stable (GitHub Releases URLs are permanent).
- Faster install than `git+https://` (no clone, just download).
- Works with `pip install <url>` and `uv tool install <url>`.

Weaknesses:
- Still requires knowing the GitHub URL.
- More CI complexity than simple git URL installs.
- aider-chat itself does NOT use this pattern — aider releases on GitHub have zero assets.
- Pure Python wheel (`py3-none-any`) works fine since aider has no compiled extensions.

**Assessment: A useful middle ground if PyPI is not wanted but faster-than-git installs are.**

### Option 4: Thin installer on PyPI + source on GitHub (aider-install pattern)

Publish only a thin `aider-relay-install` package to PyPI that:
1. Depends on `uv`.
2. On run, calls `uv tool install git+https://github.com/senanayake/aider-relay`.
3. Then calls `npm install -g @anthropic-ai/claude-code @openai/codex` (with Node.js check).

```bash
pip install aider-relay-install
aider-relay-install
```

This is exactly what aider does with `aider-install`.

Strengths:
- Familiar pattern to aider users.
- PyPI presence for discoverability with a minimal package.
- Handles npm dependency step in a single command (with appropriate Node.js check).
- The thin installer rarely changes, so PyPI publish cadence is low.

Weaknesses:
- Requires publishing two things (the installer + keeping the GitHub source correct).
- The installer always pulls `main` by default — pinning to a specific version requires extra logic.
- Any failures in the GitHub repo affect installs even if PyPI package is fine.

**Assessment: Best UX option for the target audience. Appropriate when npm installation guidance is needed as part of the install flow.**

## Quantitative Comparison

| Variable | Option 1 (git URL) | Option 2 (PyPI) | Option 3 (GH Releases) | Option 4 (thin installer) |
|----------|--------------------|-----------------|------------------------|---------------------------|
| Install friction | Medium | Low | Medium-low | Very low |
| Maintenance burden | None | Medium | Low | Low |
| Discoverability | None | High | None | Medium |
| Fork legitimacy | Clean | Clean (rename required) | Clean | Clean |
| npm dependency handled | No | No | No | Yes (with check) |
| Appropriate phase | Now (pre-stable) | Post-stable | Optional | When stable |

## Recommended Strategy: Phase-Based

### Phase 1 — Now (pre-stable development)

Use **Option 1** (git URL install). Document the four-step install (Node.js, uv, `uv tool install git+...`, `npm install -g`).

No PyPI publishing. No CI publish pipeline. Iterate fast.

```powershell
winget install OpenJS.NodeJS.LTS
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install --python python3.12 --force git+https://github.com/senanayake/aider-relay
npm install -g @anthropic-ai/claude-code @openai/codex
```

### Phase 2 — First stable release

Add **Option 3** (GitHub Release with wheel) to the CI pipeline. Tag v0.1.0, wheel is attached. Install URL is shareable and pinned.

Additionally, update `pyproject.toml`:
- `name = "aider-relay"`
- `[project.scripts]`: `aider-relay = "aider.main:main"`

### Phase 3 — Broader audience

Publish to PyPI as `aider-relay` (Option 2). Set up Trusted Publishing in GitHub Actions. Optionally publish `aider-relay-install` as the thin installer (Option 4).

## Constraints & Assumptions

- aider is Apache 2.0 licensed. Publishing a fork under a new name is legally permissible as long as the Apache 2.0 license is retained.
- The `aider-relay` name on PyPI is currently unregistered. It should be registered early (even with a placeholder 0.0.1 release) to prevent squatting.
- setuptools_scm requires `fetch-depth: 0` in GitHub Actions. This must be set in any CI workflow that builds the package.
- Node.js 22 cannot be installed by pip/uv/pipx. Any install strategy must document this separately or handle it via a thin installer with explicit Node version checks.

## Implications

- **Architecture**: The `pyproject.toml` name must be changed from `aider-chat` to `aider-relay` before any PyPI publishing. Do not publish with the upstream name.
- **Entry point**: Decide on `aider-relay` (clean separation) vs `aider` (drop-in compatibility). `aider` risks PATH conflicts for users who also have upstream aider installed. `aider-relay` is unambiguous.
- **CI**: The `setuptools_scm`-based version requires git tags. Establish a tagging convention (`vMAJOR.MINOR.PATCH-relay.N` or independent semver).

## Applicability

- Applies to: all distribution of aider-relay outside the devcontainer
- Does not apply to: devcontainer dev workflow (KB-2026-008 covers that)
