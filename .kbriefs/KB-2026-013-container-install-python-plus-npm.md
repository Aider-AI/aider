---
id: KB-2026-013
type: standard
status: validated
created: 2026-04-28
updated: 2026-04-28
tags: [container, docker, devcontainer, python, nodejs, npm, packaging, installation]
related: [KB-2026-008, KB-2026-011, KB-2026-012, KB-2026-014]
---

# Container Installation: Python CLI + npm Dependencies

## Context & Problem Statement

aider-relay requires both Python 3.12 (the application runtime) and Node.js 22 (for `@anthropic-ai/claude-code` and `@openai/codex`). Container images for aider-relay — whether for distribution (users running `docker run`) or for CI — must provide both runtimes.

This brief documents the validated patterns for building such images, with concrete Dockerfile examples.

## Standard/Pattern Description

### Core Principles

1. **Never use a single-language base image and then bolt the other on** — it creates dependency hell. Use either a purpose-built polyglot image or a multi-stage build.
2. **Node.js global installs must be accessible to the same user that runs the app** — npm's `-g` flag installs to a prefix; that prefix must be on the running user's PATH.
3. **For devcontainers, use a pre-built image** (already established in KB-2026-008). For distribution Docker images, build a custom image.

### Pattern A: Polyglot Base Image (devcontainer only)

Already established in KB-2026-008. The devcontainer uses:
```
ghcr.io/senanayake/polyglot-devcontainers-python-node:v0.0.27
```

This image provides Python 3.12 + uv + Node.js 22 + npm + task. It is the correct choice for the development environment.

**Not suitable for distribution images** — it includes dev tools (ruff, gh CLI, pre-commit, etc.) that inflate the image size.

### Pattern B: Multi-Stage Build (distribution image)

Build a lean production image by combining the official Python and Node.js slim images using multi-stage builds. This is the standard pattern for Python + Node polyglot containers.

```dockerfile
# Stage 1: Node.js — extract node/npm binaries
FROM node:22-bookworm-slim AS node

# Stage 2: Final image based on Python
FROM python:3.12-slim-bookworm

# --- System dependencies ---
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
      git \
      build-essential \
      libportaudio2 \
      pandoc \
    && rm -rf /var/lib/apt/lists/*

# --- Copy Node.js from the node stage ---
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/bin/npm /usr/local/bin/npm
COPY --from=node /usr/local/bin/npx /usr/local/bin/npx
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules

# Verify Node is working
RUN node --version && npm --version

# --- App user ---
RUN useradd -m -u 1000 -s /bin/bash appuser

# --- npm global prefix for appuser ---
ENV NPM_CONFIG_PREFIX=/home/appuser/.npm-global
ENV PATH="/home/appuser/.npm-global/bin:$PATH"

# --- Python virtual environment ---
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# --- Install Python package (from GitHub) ---
RUN /venv/bin/pip install --no-cache-dir --upgrade pip && \
    /venv/bin/pip install --no-cache-dir \
      git+https://github.com/senanayake/aider-relay

# --- Install npm packages (as appuser to respect prefix) ---
USER appuser
RUN npm install -g @anthropic-ai/claude-code @openai/codex
USER root

# --- Fix venv permissions ---
RUN chown -R appuser:appuser /venv /home/appuser/.npm-global

USER appuser

ENTRYPOINT ["/venv/bin/aider-relay"]
```

Key decisions in this Dockerfile:

- `COPY --from=node` copies only the Node binaries and the global node_modules directory — not the entire Node image. This keeps the final image small.
- npm global prefix is set to `/home/appuser/.npm-global` so npm does not require root for global installs. PATH is updated to include it.
- Python packages go into `/venv` (isolated from system Python).
- The `@anthropic-ai/claude-code` and `@openai/codex` packages are installed globally and available at `/home/appuser/.npm-global/bin/claude` and `/home/appuser/.npm-global/bin/codex`.

### Pattern C: Single Image with Node Install Script (simpler, larger)

If multi-stage complexity is unwanted, install Node from NodeSource inside a Python base image:

```dockerfile
FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

RUN node --version && npm --version

# ... rest of install as above
```

Weaknesses:
- Larger image (NodeSource installer pulls many apt packages).
- curl dependency adds attack surface.
- Harder to pin to exact Node patch versions.

**Verdict: Use multi-stage (Pattern B) for distribution images.**

### Pattern D: devcontainer from GitHub Source (no PyPI)

For a devcontainer that installs aider-relay from the GitHub source rather than from local workspace:

```json
{
  "name": "aider-relay-user",
  "image": "ghcr.io/senanayake/polyglot-devcontainers-python-node:v0.0.27",
  "postCreateCommand": "uv pip install git+https://github.com/senanayake/aider-relay && npm install -g @anthropic-ai/claude-code @openai/codex"
}
```

This is appropriate for users who want a devcontainer without cloning the repo locally.

### npm Package Versions and Credential Requirements

`@anthropic-ai/claude-code` and `@openai/codex` both require authentication at runtime (not at install time). npm install itself does not require API keys. However:

- `claude` requires `CLAUDE_CODE_OAUTH_TOKEN` or interactive `claude auth login` before first use.
- `codex` requires `OPENAI_API_KEY` or interactive login.

In devcontainers, inject these via `containerEnv` (see KB-2026-008). In distribution Docker images, document that users must mount credentials or set env vars at `docker run` time:

```powershell
docker run --rm -it `
  -e CLAUDE_CODE_OAUTH_TOKEN=$env:CLAUDE_CODE_OAUTH_TOKEN `
  -e OPENAI_API_KEY=$env:OPENAI_API_KEY `
  -v "${PWD}:/workspace" -w /workspace `
  ghcr.io/senanayake/aider-relay
```

## Key Rules

- Rule 1: Always set `NPM_CONFIG_PREFIX` to a user-writable directory when running as a non-root user in containers. The default global prefix requires root.
- Rule 2: Add the npm prefix `bin` directory to `PATH` before the `npm install -g` step.
- Rule 3: Use `node:22-bookworm-slim` as the Node source stage to match the `python:3.12-slim-bookworm` glibc/ABI compatibility.
- Rule 4: For devcontainers, prefer the pre-built polyglot image over building in postCreateCommand to keep container startup fast.

## Alternatives & Evidence

### Alternative: Use `uv` inside the container for Python install

Replace `pip install` with `uv pip install` inside Docker:

```dockerfile
RUN pip install uv && \
    uv pip install --system git+https://github.com/senanayake/aider-relay
```

This is faster (uv parallel resolver) and reproduces the same environment as uv outside containers. Note: `--system` flag is required when installing into a system Python inside Docker, or use a venv as shown above.

### Alternative: Pre-install in GitHub Actions, bake into image

Build a wheel in CI via `python -m build` and bake the wheel into the Docker image rather than cloning from GitHub at build time. This eliminates the git clone dependency inside Docker but requires a CI pipeline to publish wheels or the Docker image first.

## Verification & Compliance

After building the image, verify:
```bash
docker run --rm ghcr.io/senanayake/aider-relay aider-relay --version
docker run --rm ghcr.io/senanayake/aider-relay node --version    # should be v22.x
docker run --rm ghcr.io/senanayake/aider-relay claude --version
docker run --rm ghcr.io/senanayake/aider-relay codex --version
```

## Applicability Matrix

| Context | Pattern | Rationale |
|---------|---------|-----------|
| Developer devcontainer | A (polyglot image) | Fast startup, tools included |
| User wanting container-based install | B (multi-stage) | Lean image, correct for distribution |
| CI pipeline | B or C | Depends on whether image caching is available |
| Devcontainer without local clone | D (postCreateCommand) | Fetches from GitHub directly |
