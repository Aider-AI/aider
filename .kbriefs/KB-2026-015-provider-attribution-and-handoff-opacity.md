---
id: KB-2026-015
type: design-space
status: draft
created: 2026-04-29
updated: 2026-04-29
tags: [session-continuity, multi-turn, audit, provider-attribution, handoff, context-relay]
related: [KB-2026-007, KB-2026-006, KB-2026-010]
---

# Provider Attribution and Handoff Opacity

## Context

Prompted by "Where Is My Agent.lock File?" (Srajan Gupta, Substack 2026). The article argues that AI coding tools lack reproducibility and auditability — different model versions, skills, and configurations produce divergent output invisibly. While the article targets team workflows, it surfaces two specific failure modes that apply directly to aider-relay's single-user multi-turn relay.

## Failure Mode 1: Silent Configuration Divergence on Switch

When aider-relay switches from Claude Code to Codex, the incoming provider does not inherit the outgoing provider's execution configuration:

| Configuration dimension | Claude Code session | Codex session |
|---|---|---|
| Permission mode | `bypassPermissions` | `--sandbox workspace-write` |
| Model | Claude Sonnet/Opus (user default) | o4-mini (user default) |
| Tool set | Full Claude Code built-in tools | Codex tool set |
| Context window | 200k tokens | Model-dependent |
| Session state | Resumed via `session_id` | New thread or resumed via `thread_id` |

**The git-only handoff (KB-2026-007 Phase 1) transfers task progress but transfers zero configuration state.** The incoming provider starts with its own defaults, which may produce different code style, different safety posture, and different tool availability — silently.

This is not necessarily wrong (different providers have different strengths) but it is currently invisible. A user has no way to know whether a code change was made by Claude in `bypassPermissions` mode or Codex in `workspace-write` sandbox mode.

## Failure Mode 2: No Provider Attribution in Git History

Currently, commits made during a relay session have no record of which provider made them. If Claude Code writes a function on turn 3 and Codex extends it on turn 7 after a switch, git history is indistinguishable from a single-provider session.

This matters for:
- **Debugging**: if a bug appears, knowing which provider introduced it narrows the investigation
- **Audit**: understanding which AI made which changes
- **Reproducibility**: replaying a session requires knowing which provider was active at each step

## Design Space

### Option 1: Commit message attribution (minimal)

Append a trailer to commits made during a relay session:

```
feat: add login endpoint

Relay-Provider: claude-code (session: abc123)
Relay-Task: add OAuth login to the API
```

- **Complexity**: Low — can be injected as a git hook or by asking the provider to use this commit format
- **Limitation**: Only captures commits, not turns that didn't produce commits

### Option 2: relay.lock file (structured audit trail)

Maintain a `.aider-relay/relay.lock` (git-ignored) updated throughout the session:

```json
{
  "task": "add OAuth login",
  "started_at": "2026-04-29T10:00:00Z",
  "cycles": [
    {
      "provider": "claude-code",
      "model": "claude-sonnet-4-7",
      "session_id": "abc123",
      "permission_mode": "bypassPermissions",
      "started_at": "2026-04-29T10:00:00Z",
      "ended_at": "2026-04-29T12:45:00Z",
      "end_reason": "exhausted",
      "commits": ["a1b2c3", "d4e5f6"]
    },
    {
      "provider": "codex",
      "model": "o4-mini",
      "thread_id": "019dd791-...",
      "sandbox": "workspace-write",
      "started_at": "2026-04-29T12:45:30Z",
      "ended_at": null,
      "end_reason": null,
      "commits": []
    }
  ]
}
```

- **Complexity**: Medium — relay_loop must write this file as it runs
- **Value**: Full audit trail of which provider did what and when
- **Limitation**: Intra-session only; doesn't survive a process restart unless persisted

### Option 3: Structured handoff prompt includes config diff (targeted)

When switching providers, the handoff prompt (KB-2026-007) includes a note about configuration differences:

```
Note: The previous provider (Claude Code) operated with bypassPermissions
and access to Read/Edit/Bash/Glob tools. You (Codex) operate with
workspace-write sandbox. Adjust your approach accordingly.
```

- **Complexity**: Low — add to the handoff prompt generator
- **Value**: Helps the incoming provider calibrate its behaviour
- **Does not** address attribution in git history

## Convergence Strategy

- **Phase 1 (now):** No change needed — git-only handoff is correct for initial validation
- **Phase 2:** Add Option 3 (config diff in handoff prompt) when implementing RelayContext (KB-2026-007 Phase 2). Low cost, directly improves context quality.
- **Phase 3:** Add Option 1 (commit message attribution) via a git commit-msg hook or by instructing providers to use a trailer format.
- **Phase 4:** Add Option 2 (relay.lock) only if audit or replay requirements emerge.

## What the Article Does NOT Apply To

- The article's "team enforcement" and "policy gate" concepts are irrelevant — aider-relay is single-user with no policy enforcement layer.
- The article's "malicious skill loading" concern is irrelevant — aider-relay does not load external skills or MCP servers into providers.

## Applicability

- ✅ KB-2026-007 Phase 2: include config summary in RelayContext handoff prompt
- ✅ relay_loop.py: log which provider is active and for how long
- ⬜ Phase 3: git commit attribution
- ⬜ Phase 4: relay.lock file
