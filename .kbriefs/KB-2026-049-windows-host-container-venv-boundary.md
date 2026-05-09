---
id: KB-2026-049
type: failure-mode
status: validated
created: 2026-05-08
updated: 2026-05-08
tags: [windows, devcontainer, venv, uv, host-container-boundary, validation]
related: [KB-2026-008, KB-2026-038, KB-2026-039]
---

# Windows Host Reuse of Container Virtualenv

## Context & Significance

This repo is developed from a Windows host but executed inside a Linux devcontainer. The
workspace is shared, so `.venv` can be created in one environment and then reused from the
other. That crosses an OS boundary in a way `uv`, Python, and PortAudio-linked packages do
not tolerate reliably.

The failure matters because it produces misleading validation errors on the host and can send
agents into the wrong remediation path.

## Description

The failure occurs when a Linux-created devcontainer virtualenv is reused from the Windows
host.

- Symptoms:
  - `uv` fails with `Access is denied` while touching `.venv/lib64`
  - host-side validation appears broken even though the container environment is healthy
  - agents may try to repair packages instead of fixing the environment boundary
- When it occurs:
  - a prior agent or developer runs `task init` inside the devcontainer
  - later validation is attempted from PowerShell against the shared `.venv`
- Systems affected:
  - Windows host workflow
  - shared-workspace devcontainer setups
- User impact:
  - wasted diagnosis time
  - false negatives on `task lint` and `task test`
  - risk of mutating the wrong environment

## Root Cause Analysis

### Primary Cause

The repo uses a bind-mounted workspace. A Linux virtualenv created under `/workspaces/aider-relay`
is visible on the Windows host as `C:\Users\chris\Dev\aider-relay\.venv`. That environment
contains Linux-specific layout and metadata, including `lib64` compatibility entries and a
Linux interpreter home in `pyvenv.cfg`.

### Contributing Factors

- The host and container share the same `.venv` directory name.
- PowerShell commands can accidentally target the shared Linux venv.
- The repo historically documented a devcontainer standard, but the concrete failure mode was
  not captured.

### Failure Mechanism

When `uv` or Windows file operations touch `.venv/lib64`, they encounter a host-visible
reparse or junction entry created from the Linux side. The host sees a path that does not
behave like a normal Windows virtualenv, and cleanup/install flows fail before useful
validation can begin.

## Evidence & Reproduction

### Incidents

- Incident 1: `uv` failed on the host with `Access is denied` while attempting to remove
  `.venv/lib64`.
- Incident 2: `.venv/pyvenv.cfg` showed `home = /usr/local/bin`, confirming the environment
  came from the Linux container rather than Windows.
- Incident 3: deleting the shared `.venv`, rebuilding it inside the devcontainer, and rerunning
  validation inside the container restored normal behavior.

### Reproduction Steps

1. Run `task init` inside the devcontainer.
2. Exit to the Windows host and reuse the shared `.venv`.
3. Run host-side `uv` or validation commands against that `.venv`.
4. `uv` fails on `.venv/lib64` or related Linux-specific layout.

## Prevention & Detection

### Design Changes

- Keep the dev workflow container-native: create and use `.venv` inside the devcontainer only.
- Make repo validation run through `task dc:exec` so commands execute in the same OS context as
  the virtualenv.

### Operational Controls

- If `.venv/pyvenv.cfg` contains `/usr/local/bin`, treat the environment as container-owned.
- On Windows hosts, delete the entire `.venv` rather than trying to surgically remove
  `.venv/lib64`.
- Recreate the environment with `task dc:up` and `task dc:exec -- task init`.

### Detection Methods

- `pyvenv.cfg` points at Linux interpreter paths such as `/usr/local/bin`.
- `.venv` contains `lib64` entries or Linux-style `bin/` executables.
- `uv` fails on the host before dependency resolution starts.

### Monitoring & Alerting

- Failure signal: host-side `Access is denied` errors under `.venv`
- Environment signal: Python executable resolves to Windows on host but `/usr/local/bin/python`
  in the container

## Mitigation & Recovery

### Immediate Response

1. Stop using the shared `.venv` from the Windows host.
2. Delete the entire `.venv` directory.
3. Recreate it from inside the devcontainer with `task dc:exec -- task init`.

### Recovery Procedures

- Validate container execution with:
  - `task dc:exec -- python -c "import sys, platform; print(sys.executable); print(platform.system())"`
- Run repo checks inside the container:
  - `task dc:exec -- task lint`
  - `task dc:exec -- task test`

### Graceful Degradation

- If the container is unavailable, do not trust host validation against a container-created
  `.venv`; rebuild the environment first.

## Testing & Validation

### Test Cases

- Container rebuild: `task dc:up` followed by `task dc:exec -- task init`
- Lint validation: `task dc:exec -- task lint`
- Test validation: `task dc:exec -- task test`

## Applicability Tracking

Where this failure applies:

- ✅ Applies to: Windows host + Linux devcontainer shared workspaces
- ✅ Applies to: repos that create `.venv` inside the mounted workspace
- ❌ Does not apply to: host-native Windows virtualenvs created and used only on the host
- ❌ Does not apply to: container-only ephemeral virtualenvs outside the bind mount

## Status Checklist

- [x] Documentation complete
- [x] Prevention implemented
- [x] Detection implemented
- [x] Mitigation procedures documented
- [x] Tests passing

## Related Failures

- KB-2026-038: host/container path translation problems for git metadata follow the same
  cross-environment pattern

## Lessons Learned

Shared workspaces do not imply shared runtime artifacts. Git worktrees, virtualenvs, and other
stateful developer tooling must be treated as environment-specific unless proven otherwise.

## Recommendations

- Treat `task dc:exec` as the authoritative path for validation in this repo.
- Rebuild `.venv` when crossing the host/container boundary instead of trying to patch it in
  place.
- Prefer recording environment-boundary failures as K-Briefs early, because they masquerade as
  package or test failures.
