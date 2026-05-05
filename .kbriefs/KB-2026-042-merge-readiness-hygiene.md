# KB-2026-042: Merge-Readiness Hygiene — Post-Relay Review Protocol

**Status:** Open  
**Date:** 2026-05-03  
**Context:** Identified from Codex review of polyglot-devcontainers OpenRewrite relay run

## Problem

The first end-to-end relay run (polyglot-devcontainers, OpenRewrite feature) produced
a coherent first-slice implementation but was not merge-ready without a second-pass
review. Four categories of failure were identified:

1. **Process-vs-product blur** — `TASK.md` (relay internal transcript) was committed
   to the feature branch and treated as repo content. Internal orchestration artifacts
   should never appear in the deliverable.

2. **Doc/runtime drift** — the relay documented the dry-run patch output path as
   `build/rewrite/rewrite.patch`. Actual Gradle 9 behavior produces
   `build/reports/rewrite/rewrite.patch`. The relay made no attempt to verify its
   own documentation claims against a real run.

3. **Fact drift inside relay artifacts** — the patch mails and TASK.md claimed plugin
   version `7.32.0`; the actual branch used `7.30.0`. The relay allowed inconsistency
   between its transcript and the code it produced.

4. **Unencoded proof claims** — the relay stated "all proof paths passed" in the
   transcript, but there was no durable CI-owned validation gate (e.g. a Gradle task
   in CI that runs `rewrite:dry-run`). Proof existed only in ephemeral transcript text.

5. **Empty handoff envelope** — `session.json` had empty `files_in_scope`,
   `session_summary`, and `git` fields. The downstream reviewer had to reconstruct
   state from diffs and patches rather than reading a reliable summary.

## Root Cause

The relay has no post-run merge-readiness check. It terminates on exhaustion, writes
whatever state it managed to capture, and stops. Quality assurance is entirely
dependent on the agent's own judgment — which is unreliable for self-consistency
checks and process/product separation.

## Required Checks (Merge-Readiness Gate)

A post-relay review pass must verify:

| Check | What to look for |
|---|---|
| Process artifacts | `TASK.md`, `session.json`, `*.patch` NOT in feature branch diff |
| Doc/runtime alignment | Every path, command, or output claimed in docs has a test or CI step that validates it |
| Version consistency | Version strings in docs, configs, and changelogs all agree |
| Proof encoding | Every "proof path" from the task spec maps to a repo-owned automation step |
| Handoff envelope | `session.json` has non-empty `files_in_scope`, `session_summary`, git SHA |

## Options

**A. Human review checklist (minimum viable)**

Document the five checks above in the relay task spec template. The human reviewer
runs through them before approving a PR. No automation required.

Low cost. Depends on discipline. The Codex second-pass on OpenRewrite is an example
of this working — but it cost a full Codex session to do manually.

**B. Relay-owned post-run validation script**

`scripts/merge_check.py` — runs after the provider loop terminates. Checks:
- `session.json` completeness (non-empty fields)
- Presence of process artifacts in `git diff --name-only HEAD...<base>`
- (Optional) invokes project's own CI lint/test to confirm proof paths

Output: a `merge_readiness.md` report the downstream reviewer reads before PR approval.
Medium cost. Automatable for the structural checks; cannot automate doc/runtime alignment.

**C. Inject merge-readiness prompts at session end**

Before the relay writes the final `session.json`, it prompts the last active provider:
"Review your changes for process artifacts, doc accuracy, and proof encoding. Fix
anything that doesn't meet the merge-readiness criteria."

Cheap to implement. Unreliable — the agent that produced the problem is being asked
to self-review. Useful as a catch for obvious issues (e.g. committed TASK.md) but
not for subtler drift.

**D. Structured handoff envelope enforcement**

Make `MTARPSession.write()` refuse to write if `files_in_scope` or `session_summary`
are empty, or if `git.head` does not match `git rev-parse HEAD`. Forces the relay
to populate the envelope before terminating.

Addresses gap 5 directly. Does not address gaps 1–4.

## Recommendation

**Implement in order:**

1. **Option D** — enforce non-empty handoff envelope in `MTARPSession.write()`. This
   is a relay code change and fixes the most concrete measurable failure.

2. **Option C** — add a merge-readiness self-review prompt to the relay's final turn.
   Cheap; catches the obvious cases (TASK.md, version strings).

3. **Option A** — ship a merge-readiness checklist in the TASK.md template used by
   `relay.sh`. Human reviewer uses it before marking a PR ready.

4. **Option B** — defer `merge_check.py` until the checklist in Option A has been
   validated by 2–3 relay runs. Automate what is consistently failing.

## Process Rule (Immediate)

Until automation exists:

> **aider-relay produces a first-slice implementation, not a merge-ready branch.**
> Always follow a relay run with a merge-readiness pass that checks the five criteria
> above before opening or approving a PR.

## Related

- KB-2026-038: Handoff envelope gaps (git credential and worktree path)
- Phase 2 session fields (`files_in_scope`, `session_summary`) — implemented in
  `c199c7fd7` but not populated during the OpenRewrite run
- Codex review of polyglot-devcontainers `feat/java-openrewrite` (2026-05-03)
