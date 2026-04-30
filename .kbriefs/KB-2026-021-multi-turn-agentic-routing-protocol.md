---
id: KB-2026-021
type: design-space
status: draft
created: 2026-04-29
updated: 2026-04-30
tags: [protocol, multi-turn, agentic-routing, open-standard, session-continuity, handoff, interoperability, a2a-extension]
related: [KB-2026-007, KB-2026-015, KB-2026-016, KB-2026-017, KB-2026-018, KB-2026-019, KB-2026-020, KB-2026-025, KB-2026-026]
---

# Multi-Turn Agentic Routing Protocol (MTARP)

## The Gap

> **Updated 2026-04-30:** KB-2026-025 found that the original framing overstated the gap vs A2A.
> KB-2026-026 repositions MTARP as a formal A2A extension rather than a competing protocol.
> The claims below have been sharpened accordingly.

Every existing agent interoperability effort targets one of two problems:

- **Task delegation** (Google A2A, April 2025): agent A assigns a fresh, well-defined task to agent B. Clean handoff of a *new* task.
- **Tool/resource access** (Anthropic MCP): how an agent accesses external tools and data. Inbound to agent, not between agents.

A2A's `contextId` + `history[]` + `artifacts[]` can approximate session continuation through orchestrator-driven re-submission, but it does not natively support **exhaustion-triggered continuation with git-aware context**. Specifically, A2A has no:

- Pre-exhaustion warning state (`approaching_limit`)
- Handoff trigger taxonomy distinguishing *why* a task ended (routing-relevant semantics)
- Git-aware context delivery (diff_since SHA anchoring what the outgoing agent changed)
- Tier-specific delivery mode (pull vs push vs push-tools depending on incoming agent type)

These gaps — not the broader claim that "A2A doesn't handle session continuation" — are what MTARP adds. MTARP is therefore positioned as a **domain-specific A2A extension** for git-based coding agents (KB-2026-026), not a competing protocol.

## Core Constraint (Non-Negotiable)

Tier A agentic CLI providers (Claude Code, Codex) maintain server-side session state that **cannot be transferred** (KB-2026-017). The protocol can never achieve full session state fidelity for Tier A. The design goal is therefore not "transfer all state" but "transfer enough context that the incoming agent can continue without user re-explanation."

This is a different and more achievable goal. It shifts the protocol from a state-transfer problem to a context-relay problem.

## The Universal Substrate: Git

Across all provider types, tiers, and deployment environments, one artifact is always present, always objective, and always lossless: **the git repository**. Git captures all file changes with timestamps, authorship, and message. Any agent can read it. No coordination is required to produce it — the outgoing agent's edits are automatically captured.

The protocol is therefore **git-first**: the minimum viable handoff is a git ref (commit SHA) plus a task description. All richer context layers are additive.

## Protocol Primitives

### 1. Session Envelope (`session.json`)

A versioned, provider-agnostic JSON document written to `.aider-relay/session.json` (or a configurable path). Written by the relay/outgoing agent; read by the incoming agent as its first act.

**Core fields (mandatory — minimum viable handoff):**

```json
{
  "schema_version": "1.0",
  "session_id": "<uuid>",
  "task": {
    "description": "Add OAuth login to the API",
    "created_at": "2026-04-29T10:00:00Z"
  },
  "git": {
    "head": "<commit-sha>",
    "branch": "feature/oauth",
    "diff_since": "<sha-at-session-start>"
  },
  "handoff": {
    "reason": "exhausted",
    "at": "2026-04-29T12:45:00Z",
    "outgoing_provider": "claude-code",
    "outgoing_tier": "agentic_cli"
  }
}
```

**Standard fields (Phase 2 — structured progress):**

```json
{
  "subtasks": [
    {"id": 1, "description": "Add /auth/login endpoint", "status": "done"},
    {"id": 2, "description": "Add JWT token generation", "status": "in_progress"},
    {"id": 3, "description": "Add /auth/refresh endpoint", "status": "pending"}
  ],
  "provider_history": [
    {
      "provider": "claude-code",
      "tier": "agentic_cli",
      "session_id": "abc123",
      "model": "claude-sonnet-4-7",
      "config": {"permission_mode": "bypassPermissions"},
      "started_at": "2026-04-29T10:00:00Z",
      "ended_at": "2026-04-29T12:45:00Z",
      "end_reason": "exhausted",
      "commits": ["a1b2c3", "d4e5f6"]
    }
  ],
  "files_in_scope": ["src/api/auth.py", "src/models/user.py"]
}
```

**Rich fields (Phase 3+ — reasoning context):**

```json
{
  "key_decisions": [
    "Using PyJWT library for token generation",
    "Refresh tokens stored in Redis, not in DB"
  ],
  "session_summary": "<LLM-generated summary of what was done and why>",
  "routing_hints": {
    "estimated_complexity": "medium",
    "requires_tools": true,
    "requires_large_context": false,
    "preferred_next_tier": "agentic_cli"
  }
}
```

### 2. Handoff Trigger Taxonomy

A closed enum of reasons a session transfer occurs. The incoming agent uses this to calibrate its starting posture:

| Reason | Meaning | Incoming agent implication |
|---|---|---|
| `exhausted` | Outgoing provider hit usage limit | Continue from git state; prior work is complete up to last commit |
| `escalate` | Task too complex for current provider | Prior provider made a best-effort attempt; verify its output before continuing |
| `deescalate` | Task simplified; cheaper provider sufficient | Earlier work at higher tier; continue with reduced context requirements |
| `user_request` | User explicitly requested switch | No failure; full context available |
| `error` | Provider failed non-exhaustion failure | Prior output may be incomplete or incorrect; verify before continuing |

### 3. Provider Capability Advertisement (A2A Agent Card + MTARP extension)

> **Updated 2026-04-30:** A standalone `agent-card.json` is dropped. Use an A2A Agent Card
> with an MTARP extension namespace instead (KB-2026-026). This makes MTARP-compliant agents
> also A2A-compatible.

```json
{
  "name": "claude-code",
  "capabilities": {
    "streaming": true,
    "extensions": [
      {
        "uri": "https://mtarp.dev/ext/coding-session/v1",
        "required": false,
        "params": {
          "tier": "agentic_cli",
          "delivery_mode": "pull"
        }
      }
    ]
  }
}
```

**Delivery mode** is the key field:
- `pull`: agent reads files autonomously (Tier A); relay injects task + git ref only
- `push`: agent receives file contents in prompt (Tier B); relay injects full file contents
- `push-tools`: agent receives tool definitions and calls them via relay (Tier C)

### 4. Health Event Schema

Standard events that a compliant provider emits during a session. The relay acts on these to trigger handoffs:

```json
{
  "event_type": "health",
  "status": "exhausted | approaching_limit | transient_error | permanent_error",
  "reset_at": "<iso-timestamp or null>",
  "error_kind": "transient | permanent | rate_limit | not_available",
  "message": "<human-readable detail>"
}
```

This standardises the currently provider-specific signals: Claude Code's `RateLimitEvent`, Codex subprocess exit codes, Ollama HTTP errors.

## Handoff Matrix (Tier-Aware Delivery)

The protocol defines required delivery behaviour for each tier-to-tier transition:

| From \ To | Tier A (pull) | Tier B (push) | Tier C (push-tools) |
|---|---|---|---|
| **Tier A** | git diff + task + config summary | git diff + task + file contents | git diff + task + tool defs |
| **Tier B** | message history + task | message history carry-forward | message history + tool defs |
| **Tier C** | message history + task | message history + file contents | message history carry-forward |

A compliant relay must implement the delivery mode declared in the incoming agent's `agent-card.json`.

## Design Tensions

### 1. Opaque state ceiling
Tier A session state is server-side and non-transferable. The protocol cannot overcome this — it can only minimise the impact by ensuring the incoming agent has enough external context (git, task, subtasks) to continue without the lost state. The success criterion is "user does not need to re-explain", not "incoming agent has identical context".

### 2. Who writes the envelope?
If the outgoing agent is exhausted, it may be unable to generate a rich handoff brief. The relay must be capable of generating a minimum viable envelope from git alone, without outgoing agent participation. The protocol therefore specifies two writing modes:
- **Proactive** (preferred): outgoing agent writes envelope at logical task boundaries
- **Emergency** (fallback): relay generates minimum viable envelope from git at handoff time

### 3. File vs. wire transport
A2A is HTTP-based. A file-based protocol (session.json in the repo) has near-zero adoption friction — any project can implement it by reading and writing a JSON file. HTTP transport is an optional layer on top, not a requirement. The protocol is **file-first**.

### 4. Standardisation vs. extensibility
A lowest-common-denominator schema enables broad adoption but may be insufficient for specific providers. The protocol uses **extension namespaces**: any field in `extensions.<namespace>.*` is provider-specific and may be ignored by non-implementing agents. Core fields must be supported by all compliant agents.

## Relationship to Existing Protocols

| Protocol | Problem solved | Relation to MTARP |
|---|---|---|
| Google A2A | Task delegation between agents | **MTARP extends A2A** — session.json is an A2A artifact; agent card is an A2A AgentCard with MTARP extension namespace; health events extend A2A SSE |
| Anthropic MCP | Tool/resource access for agents | Orthogonal — MCP is inbound to agent; MTARP is between agents |
| OpenAI Assistants threads | Session persistence within OpenAI | Subset — threads work only within one provider; MTARP is cross-provider |
| LangGraph/CrewAI handoff | Framework-specific agent handoff | Framework-specific; MTARP is the protocol layer those frameworks could implement |

## Validation Requirements

Before MTARP can be proposed as a standard, these must be empirically demonstrated:

1. **Continuation coherence**: The same session envelope produces coherent continuation in at least two different agents (e.g., Claude Code and Codex). The `--sim-exhaust-after` test in aider-relay is the validation harness for this.

2. **Handoff quality measurement**: A benchmark (RouterBench-style) that scores whether the incoming agent continued the task correctly given the envelope. Without a score, "compliant" is not verifiable.

3. **Provider health event standardisation**: At least two providers must emit health events in the standard schema. Currently only Claude Code emits pre-exhaustion signals — Codex has no equivalent.

4. **Non-commit task handoff**: For tasks that produce no git commits (planning, Q&A, code review), git provides no context. The protocol must have a validated fallback for this case.

## Convergence Strategy (Protocol Maturity Phases)

| Phase | Protocol milestone | aider-relay milestone |
|---|---|---|
| 0 (now) | Informal git-only handoff (KB-2026-007 P1) | relay_loop.py with sim_exhaust |
| 1 | Schema v0.1: core envelope fields + handoff trigger taxonomy | Write session.json on exhaustion |
| 2 | Schema v0.2: standard fields (subtasks, provider_history, config) | RelayContext (KB-2026-007 P2) |
| 3 | Agent-card.json + delivery mode enforcement | Add Ollama as Tier B provider |
| 4 | Health event schema standardised; validate cross-tier continuation | Validate Tier A→B handoff |
| 5 | Handoff quality benchmark published; schema v1.0 declared stable | RouterBench-style eval harness |

## Open Questions

1. ~~**Is "session continuation" sufficiently distinct from A2A task delegation** to justify a separate protocol?~~ **Resolved (KB-2026-025, KB-2026-026):** MTARP is a domain-specific A2A extension, not a competing protocol. The genuinely distinct contributions are git-first context, exhaustion trigger taxonomy, and tier-aware delivery — not a new wire protocol.
2. **Can the protocol handle multi-agent parallelism** (two agents working on different files simultaneously, then merging)? Git branches are the natural mechanism, but the session envelope would need to express a merge event, not just a handoff.
3. **Who maintains the schema?** An open standard requires a governance body or at minimum a versioned spec repo. Should this be published under aider-relay's GitHub org, or proposed to an existing agent interoperability working group?
4. **Does the Routesplain task taxonomy** (KB-2026-018) belong in `routing_hints.estimated_complexity` or should it be a separate `task_taxonomy` field? A richer taxonomy helps the router but increases envelope verbosity.

## Applicability to aider-relay

- ✅ aider-relay is the reference implementation — `session.json` should be written on every exhaustion event starting Phase 1
- ✅ Phase 1 schema maps directly onto KB-2026-007 git-only handoff — zero additional work to write the file
- ✅ `handoff_reason` enum resolves the KB-2026-020 `error_kind` ambiguity — one field covers both
- ✅ `agent-card.json` is the formal expression of KB-2026-019's delivery mode concern
- ✅ The protocol validation requirements define the exact test suite needed for Phase 4
