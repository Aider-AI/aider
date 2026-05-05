# Task: <short title>

## What you are building

<One paragraph: the feature, bug fix, or change being made. Be specific about scope.>

## Authoritative specifications

Read these files before writing any code:
- `<path/to/spec-or-kb.md>` — <what it contains>

## Exact files to create/modify

<!-- List every file. For modifications, describe what changes. -->

### CREATE: `<path>`
<What goes in it.>

### MODIFY: `<path>`
<What changes and why.>

## Proof paths

<!-- Every claim about correctness must map to a runnable check. -->

| Claim | Proof command |
|---|---|
| Tests pass | `task test` |
| Lint clean | `task lint` |
| <feature-specific claim> | `<command that verifies it>` |

## Acceptance criteria

- [ ] <Criterion 1 — specific, testable>
- [ ] <Criterion 2>
- [ ] All proof paths above pass

## Execution gateway

<!-- relay.sh populates this when --container or --workspace-folder is given. -->
<!-- Replace the placeholder with the actual gateway command before running.  -->

All build, test, and git-write commands run inside the devcontainer, not the host:

```
<EXEC_GATEWAY> <command>
# e.g. devpod exec polyglot-devcontainers -- ./gradlew build
# e.g. devcontainer exec --workspace-folder /workspaces/polyglot-devcontainers -- task test
```

File reads and git read operations (`status`, `log`, `diff`) may run on the host.

## Non-goals

<!-- What is explicitly out of scope for this task. -->
- Do NOT install system packages on the host (`apt`, `npm install -g`, `pip install` outside venv)
- Do NOT commit relay-internal files (`TASK.md`, `session.json`, `*.patch`)
- Do NOT modify CI configuration unless the task explicitly requires it

## Merge-readiness checklist

Before considering this task done, verify:

- [ ] **Process artifacts absent** — `TASK.md`, `session.json`, patch files are NOT committed to the branch
- [ ] **Doc/runtime alignment** — every path and command in docs matches what the code actually produces (run a check)
- [ ] **Version consistency** — version strings in docs, configs, and changelogs agree
- [ ] **Proof encoded** — every acceptance criterion has a repo-owned automation step (not just a transcript claim)
- [ ] **Handoff envelope populated** — `.aider-relay/session.json` has non-empty `files_in_scope` and `session_summary`
