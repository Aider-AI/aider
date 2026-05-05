# KB-2026-044: Polyglot Orchestration — aider-relay as Environment Selector

**Status:** Open (vision captured; single-container implemented)
**Date:** 2026-05-03

## The model

aider-relay is not just a Claude/Codex switcher. It is a master orchestrator
that selects the right execution environment for each task.

**polyglot-devcontainers** (`github.com/senanayake/polyglot-devcontainers`) is a
catalogue of purpose-built images. aider-relay selects one per task:

```
aider-relay (orchestrator — Windows host or relay container)
    │
    ├── Task: build Java microservice
    │   └── --image ghcr.io/.../polyglot-devcontainers-java:v0.1.0
    │       └── podman exec aider-relay-my-project-20260503 ./gradlew build
    │
    ├── Task: build Python data pipeline
    │   └── --image ghcr.io/.../polyglot-devcontainers-python-node:v0.0.27
    │       └── podman exec aider-relay-my-project-20260503 task test
    │
    └── Task: complex multi-language system (future)
        ├── Java container   → backend services
        └── Python container → data layer / scripts
```

## Currently implemented

The `--image` flag on `relay.ps1` and `relay.sh`:

1. Derives a container name: `aider-relay-<repo-dirname>-<timestamp>`
2. Runs `podman run -d --name <name> -v <repo>:/workspaces/<dirname> -w /workspaces/<dirname> <image> sleep infinity`
3. Sets exec gateway to `podman exec <name>`
4. Applies host trust boundary (`claude-settings.json`)
5. On relay exit: `podman stop && podman rm` (ephemeral by default)
   Use `--keep-container` to retain for inspection.

Override the container-side mount path with `--container-path /workspaces/custom-name`.

## What the image provides

The polyglot image is the entire execution environment:
- Language runtimes and build tools (JDK + Gradle, Node, Python + uv, etc.)
- git config and — when credentials are passed as env vars — push capability
- Task runner (`task`), linters, test frameworks
- No need to install anything at relay time; the image is the contract

## Credential injection (open gap)

The container created by `--image` inherits no credentials from the host by default.
For git push and API calls inside the container, secrets must be injected:

```bash
# Pass GH_TOKEN into the container at creation time
podman run -d -e GH_TOKEN="$env:GH_TOKEN" ...
```

`relay.ps1` / `relay.sh` do not yet support `--env` pass-through to `podman run`.
Interim: set secrets in the polyglot image itself (not recommended for tokens),
or extend the relay scripts with `--container-env KEY=VALUE` forwarding.

## Multi-container future (not yet implemented)

A complex system task might need to switch execution environments mid-session:
- MTARP session envelope would need to record which container each provider run used
- `relay_loop.py` would need a container-selector per task phase
- The TASK.md template would specify which image handles which deliverable

This is a significant extension; file it when the single-container case is proven.

## Related

- KB-2026-039: Host trust boundary and exec gateway enforcement
- KB-2026-043: Distribution modes (Windows host vs headless container)
- KB-2026-038: Git credentials in container (needed before agents can push)
