---
id: KB-2026-026
type: specification
status: active
created: 2026-04-30
updated: 2026-04-30
tags: [mtarp, a2a, extension-spec, protocol, session-continuation, git-aware]
related: [KB-2026-021, KB-2026-022, KB-2026-025]
---

# MTARP as a Formal A2A Extension

## Status

This KB supersedes the standalone MTARP protocol framing in KB-2026-021 and KB-2026-022.
MTARP is now positioned as a domain-specific A2A extension for git-based coding agents, not
a separate transport protocol. KB-2026-025 established the rationale; this KB specifies the
technical form.

---

## Extension Identity

```
URI:         https://mtarp.dev/ext/coding-session/v1
Short name:  mtarp-cs
Version:     1.0
Domain:      git-based coding agent session continuation
Status:      draft / pre-publication
```

The URI serves as the globally unique extension identifier in A2A AgentCard declarations and
metadata namespacing. All MTARP metadata keys on A2A objects use the form:

```
https://mtarp.dev/ext/coding-session/v1/<fieldname>
```

---

## AgentCard Declaration

An agent advertising MTARP support adds the extension to its `capabilities.extensions[]` array
in its A2A Agent Card:

```json
{
  "name": "claude-code",
  "version": "1.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "extensions": [
      {
        "uri": "https://mtarp.dev/ext/coding-session/v1",
        "description": "Git-aware session continuation for exhaustion-triggered handoffs",
        "required": false,
        "params": {
          "tier": "agentic_cli",
          "delivery_mode": "pull",
          "handoff_signals": ["exhausted", "escalate", "deescalate", "error"]
        }
      }
    ]
  },
  "skills": [
    {
      "id": "code-edit",
      "name": "Code editing",
      "description": "Reads and edits files in a git repository to complete a coding task",
      "inputModes": ["text/plain"],
      "outputModes": ["text/plain"]
    }
  ],
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"]
}
```

### Extension params schema

| Field | Type | Values | Meaning |
|---|---|---|---|
| `tier` | string | `agentic_cli`, `completion_api`, `hybrid` | How this agent receives context |
| `delivery_mode` | string | `pull`, `push` | Whether to inject file contents (push) or git ref (pull) |
| `handoff_signals` | string[] | subset of trigger enum | Which handoff reasons this agent can receive |

**`tier` governs incoming context delivery:**

- `agentic_cli` — Agent has filesystem access. Router injects task + git ref only (SHA range).
  Agent runs `git diff <diff_since>..HEAD` itself.
- `completion_api` — Agent has no filesystem access. Router injects full file contents.
- `hybrid` — Agent has tool access. Router injects tool definitions + git context.

`required: false` means: an A2A orchestrator that does not understand MTARP can still call
this agent normally — the extension degrades gracefully to standard task semantics.

---

## Session Artifact Schema

When MTARP session state is carried over A2A, `session.json` is expressed as an A2A
**Artifact** in the task's `artifacts[]` array, not as a separate sidecar file.

### Artifact declaration on an A2A Task

```json
{
  "artifactId": "mtarp-session-<session-uuid>",
  "name": "mtarp-session",
  "mimeType": "application/json",
  "description": "MTARP session envelope for handoff continuation",
  "extensions": [
    "https://mtarp.dev/ext/coding-session/v1"
  ],
  "parts": [
    {
      "kind": "text",
      "text": "{ ...session.json contents... }"
    }
  ]
}
```

### session.json schema (unchanged)

The session.json content itself is the existing MTARP schema (KB-2026-021 §3):

```json
{
  "schema_version": "1.0",
  "session_id": "<uuid>",
  "task": {
    "description": "add OAuth login",
    "created_at": "2026-04-30T10:00:00Z"
  },
  "git": {
    "head": "<current-sha>",
    "branch": "main",
    "diff_since": "<session-start-sha>"
  },
  "handoff": {
    "reason": "exhausted",
    "at": "2026-04-30T11:30:00Z",
    "outgoing_provider": "claude-code",
    "outgoing_tier": "agentic_cli"
  },
  "provider_history": [
    {
      "provider": "claude-code",
      "tier": "agentic_cli",
      "session_id": "<provider-internal-id>",
      "started_at": "2026-04-30T10:00:00Z",
      "ended_at": "2026-04-30T11:30:00Z",
      "end_reason": "exhausted"
    }
  ]
}
```

The session.json schema is the artifact's payload. Its JSON structure is defined by MTARP;
its transport container is A2A.

---

## Task Metadata Namespacing

For MTARP data that belongs on the Task object itself (rather than in the session artifact),
use the `metadata` map with fully namespaced keys:

```json
{
  "id": "task-xyz",
  "contextId": "session-X",
  "metadata": {
    "https://mtarp.dev/ext/coding-session/v1/handoff_reason": "exhausted",
    "https://mtarp.dev/ext/coding-session/v1/git_diff_since": "abc123def456",
    "https://mtarp.dev/ext/coding-session/v1/outgoing_tier": "agentic_cli"
  }
}
```

This allows an MTARP-aware orchestrator to inspect handoff signals from a Task object
without parsing the full artifact — useful for routing decisions before retrieving artifact
contents.

---

## Health Event: `approaching_limit` Signal

A2A's task state machine has no pre-exhaustion warning state. MTARP adds one as an extension
on A2A's SSE streaming.

### MTARP health event (sent over A2A SSE stream)

```json
{
  "type": "mtarp_health",
  "extensions": ["https://mtarp.dev/ext/coding-session/v1"],
  "status": "approaching_limit",
  "metadata": {
    "https://mtarp.dev/ext/coding-session/v1/estimated_turns_remaining": 3,
    "https://mtarp.dev/ext/coding-session/v1/limit_type": "daily_tokens"
  }
}
```

`approaching_limit` maps to no existing A2A task state. An MTARP-aware orchestrator
receiving this signal should:
1. Begin preparing the handoff context (session artifact) while the current agent is still
   working
2. Pre-warm the incoming provider if possible (send task + context before exhaustion occurs)

An orchestrator that does not understand MTARP extension events receives this as an
unrecognized SSE event type and ignores it — graceful degradation.

### Full health status taxonomy and A2A mapping

| MTARP status | A2A task state | Routing action |
|---|---|---|
| `approaching_limit` | (no equivalent — MTARP-only) | Pre-warm incoming provider |
| `exhausted` | `FAILED` with `code: "RESOURCE_EXHAUSTED"` | Hand off with session artifact |
| `transient_error` | `FAILED` with `retryable: true` | Retry same provider |
| `permanent_error` | `FAILED` terminal | Escalate or abort |

---

## Handoff Trigger Taxonomy (extension to A2A FAILED)

A2A's FAILED state carries no routing-relevant semantics. MTARP extends it with structured
`handoff_reason` values expressed in task metadata:

```json
{
  "metadata": {
    "https://mtarp.dev/ext/coding-session/v1/handoff_reason": "exhausted"
  }
}
```

| `handoff_reason` | Meaning | Incoming agent action |
|---|---|---|
| `exhausted` | Prior work committed cleanly; limit reached | Continue from git HEAD |
| `escalate` | Task requires a more capable model | Verify prior work, then continue |
| `deescalate` | Task reduced in scope; cheaper model sufficient | Continue from git HEAD |
| `user_request` | User explicitly triggered provider switch | Treat as fresh continuation |
| `error` | Prior agent left files in inconsistent state | Audit `git diff <diff_since>..HEAD` before proceeding |

---

## Git-First Context Delivery (agentic_cli tier)

For `tier: agentic_cli` agents, the router sends the incoming task as:

```
You are continuing a coding task previously worked on by another agent.

## Task
<task.description>

## Session context
A previous agent (claude-code) worked on this task. Handoff reason: exhausted.
The session state is in the MTARP artifact attached to this task.

## Git context
The prior agent's work is captured in git. Run:
  git diff <git.diff_since>..<git.head>
to see exactly what was done. The current HEAD is <git.head>.

Continue from the current state of the working tree.
```

This is lossless: the incoming agent can reconstruct everything the outgoing agent did
from the git history. No narration from the outgoing agent is required.

---

## Current Implementation Notes (aider-relay)

aider-relay currently runs without an A2A transport layer — it drives CLI tools as
subprocesses, not HTTP agents. The MTARP extension spec describes the *target* architecture
for when A2A-compliant wrappers exist for Claude Code and Codex.

**Current state (file-first, pre-A2A):**
- `aider/relay/session.py` — MTARPSession writes session.json to disk at `.aider-relay/session.json`
- `scripts/relay_loop.py` — reads and writes session.json on exhaustion
- session.json format is compliant with the MTARP artifact schema above; it can be
  embedded directly in an A2A artifact when transport support is added

**Migration path to A2A transport:**
1. Wrap Claude Code CLI in a thin HTTP server implementing A2A's `tasks/send` RPC
2. Wrap Codex CLI similarly
3. Replace relay_loop.py's subprocess calls with A2A JSON-RPC calls
4. Express session.json as an A2A artifact (already schema-compatible)
5. Declare the extension in each agent's AgentCard

**No changes to session.json schema are required** for A2A compatibility — the schema was
designed to be forward-compatible with this embedding.

---

## Proposed A2A Contribution: `approaching_limit` Signal

The `approaching_limit` health event (§ Health Event above) addresses a genuine gap in A2A.
The proposal for a contribution to A2A v1.x:

- **Signal type:** New SSE event type `TaskApproachingLimitEvent` (analogous to
  `TaskStatusUpdateEvent`)
- **Fields:** `estimatedTurnsRemaining`, `limitType` (tokens/time/cost), `recommendedAction`
  (continue/prepare_handoff)
- **Scope:** Any A2A agent that has pre-exhaustion awareness can emit this; orchestrators
  that understand it can pre-warm fallbacks

This is independent of MTARP's git-aware specifics and would benefit any A2A routing
implementation. Should be proposed as a standard extension to the A2A working group after
aider-relay has operational experience with it.

---

## What Changed From KB-2026-021/022

| Was (standalone MTARP) | Now (MTARP as A2A extension) |
|---|---|
| Defines own wire protocol | Extends A2A JSON-RPC via metadata namespacing |
| Defines own agent-card.json | Uses A2A AgentCard with extension params |
| session.json is a sidecar file | session.json is an A2A artifact payload |
| Health events are MTARP-proprietary | Health events extend A2A SSE stream |
| Competing with A2A | Composable with A2A; degrades gracefully if A2A ignores extension |

**Unchanged:**
- Git-first context delivery (git.diff_since SHA, tier-governed injection)
- Exhaustion trigger taxonomy (the five handoff_reason values)
- session.json JSON structure
- File-first adoption for current CLI tools (no HTTP server required today)
- Provider tier model (agentic_cli / completion_api / hybrid)
