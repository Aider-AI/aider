---
id: KB-2026-022
type: standard
status: draft
created: 2026-04-29
updated: 2026-04-29
tags: [protocol, mtarp, multi-turn, agentic-routing, open-standard, session-continuity, handoff, interoperability]
related: [KB-2026-021, KB-2026-007, KB-2026-017, KB-2026-019, KB-2026-016]
---

# Multi-Turn Agentic Routing Protocol (MTARP)

## Context & Problem Statement

When an AI coding agent hits its usage limit, capability ceiling, or cost threshold mid-task, the user today must re-explain the entire task to the next agent. There is no standard way for one agent to hand off an in-progress work session to another.

This is not a niche case. Any architecture that routes across providers — local LLMs for cheap tasks, subscription CLIs for complex coding, frontier APIs for hard problems — will trigger mid-session switches regularly. Every multi-agent CI pipeline, every cost-tiered coding assistant, every team workflow with model quotas has this problem. No standard exists for it.

The two most prominent agent interoperability protocols do not solve it:

- **Google A2A (April 2025)** addresses *task delegation*: agent A assigns a well-defined new task to agent B. This is a clean handoff with no in-flight state.
- **Anthropic MCP** addresses *tool and resource access*: how a model calls external tools and data sources. It is inbound to an agent, not between agents.

Neither protocol handles *session continuation*: agent A was mid-task, stopped for any reason, and agent B must continue from that exact point without the user re-explaining.

MTARP fills this gap.

## Protocol Description

### Core Principles

**1. Git is the ground truth.**
Every agentic coding workflow runs in a git repository. Git captures all file changes continuously, objectively, and losslessly. It is readable by any agent regardless of which provider produced the changes. MTARP makes git the canonical record of what was done, and specifies a thin envelope for the one thing git cannot capture: *intent*.

**2. Continuation, not full state transfer.**
Tier A agentic providers (Claude Code, Codex) maintain server-side session state that is opaque and non-portable. MTARP does not attempt to transfer it. The success criterion is: *the incoming agent can continue without the user re-explaining* — not *the incoming agent has identical context to the outgoing agent*. This is a more achievable goal and the practically valuable one.

**3. Tier-aware delivery.**
Different agent types need context delivered differently. Tier A agents (agentic CLI) pull files themselves — they need only a task description and a git reference. Tier B agents (completion APIs) need file contents injected into the prompt. Tier C agents (hybrid tool-use) need tool definitions provided. MTARP specifies which delivery mode is required for each tier pair and enforces it via a provider capability declaration.

**4. File-first, no infrastructure required.**
MTARP is a JSON file (`session.json`) in the repository. Adopting it requires reading and writing a file. No HTTP server, no central registry, no SDK dependency. HTTP transport is an optional extension; it is not a protocol requirement.

**5. Progressive enrichment.**
The protocol defines a minimum viable envelope (git SHA + task description) that is always sufficient for a basic handoff. Richer context — subtask checklists, provider history, key decisions, LLM-generated summaries — is additive. A project can implement Phase 1 compliance in a dozen lines and grow toward full compliance incrementally.

### The Session Envelope

The core protocol artefact is `session.json`, written to `.aider-relay/session.json` (or a configurable path). It is written by the outgoing agent or relay at handoff time and read by the incoming agent as its first act.

**Phase 1 — Minimum viable (git ref + task + reason):**

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

**Phase 2 — Standard (structured progress):**
Adds `subtasks[]`, `provider_history[]`, `files_in_scope[]`, and `config_summary` (permission mode, model, tool set of the outgoing provider).

**Phase 3 — Rich (reasoning context):**
Adds `key_decisions[]`, `session_summary` (LLM-generated), and `routing_hints` (complexity estimate, required capabilities, preferred incoming tier).

### Handoff Trigger Taxonomy

A closed enum of reasons a session transfer occurs. This is the information git cannot provide — not just *that* a switch happened, but *why*. The incoming agent uses this to calibrate its starting posture:

| Reason | Meaning | Incoming agent implication |
|---|---|---|
| `exhausted` | Usage window depleted | Continue from git state; prior work done up to last commit |
| `escalate` | Task exceeds current provider capability | Audit prior work before proceeding |
| `deescalate` | Task simplified; cheaper provider sufficient | Full context available; proceed with reduced requirements |
| `user_request` | Explicit user switch | No failure; full context available |
| `error` | Provider failed for non-exhaustion reason | Prior output may be incomplete; verify before continuing |

### Provider Capability Declaration (`agent-card.json`)

A static file declaring what a compliant agent can do and what it requires at handoff time:

```json
{
  "provider": "claude-code",
  "tier": "agentic_cli",
  "context_window_tokens": 200000,
  "can_read_files": true,
  "can_write_files": true,
  "can_run_shell": true,
  "handoff_requirements": {
    "delivery_mode": "pull",
    "minimum_envelope_fields": ["task.description", "git.head"]
  }
}
```

`delivery_mode` is the key field: `pull` (agent reads files autonomously) or `push` (relay injects file contents) or `push-tools` (relay provides tool definitions and handles calls). A compliant relay selects the delivery mode declared by the incoming agent.

### Health Event Schema

Standard events a compliant provider emits during a session, enabling the relay to trigger handoffs before failures rather than after:

```json
{
  "event_type": "health",
  "status": "approaching_limit | exhausted | transient_error | permanent_error",
  "reset_at": "<iso-timestamp or null>",
  "error_kind": "transient | permanent | rate_limit | not_available",
  "message": "<human-readable detail>"
}
```

This standardises currently provider-specific signals: Claude Code's `RateLimitEvent`, Codex subprocess exit codes, Ollama HTTP errors, direct API 429 responses — all mapped to the same schema.

## What Is Unique About MTARP

### It solves the right problem
Session continuation after mid-task interruption is not addressed by any existing protocol. A2A, MCP, OpenAI Assistants threads, and framework-specific handoff mechanisms (LangGraph, CrewAI) each solve adjacent problems. MTARP is the first specification that addresses the handoff of *in-progress agentic work sessions* across *heterogeneous providers*.

### It is honest about what cannot be transferred
By explicitly acknowledging the opacity of Tier A session state and redefining the success criterion to "continue without user re-explanation," MTARP avoids the failure mode of protocols that promise more than they can deliver. The constraint is documented; the design accepts it rather than papering over it.

### Git as the universal substrate makes it genuinely cross-provider
Any agent that can run `git log` and `git diff` can read MTARP handoff context. This is not theoretical — it is true of every agent type today. No provider needs to implement a proprietary API surface for MTARP to work with it. The git-first design means the protocol has inherent backward compatibility with every coding workflow that already uses git.

### The handoff trigger taxonomy is new
No existing protocol communicates *why* a session transfer occurred. This information changes what the incoming agent should do: an `exhausted` handoff means prior work is complete and committed; an `escalate` handoff means prior output should be reviewed before proceeding; an `error` handoff means the last committed state may not reflect the user's intent. This single enum adds significant intelligence to the incoming agent's startup behaviour at near-zero implementation cost.

### Adoption is frictionless by design
Phase 1 compliance is writing a JSON file. There is no infrastructure to deploy, no SDK to pin, no central authority to register with. The protocol can be adopted by any project that orchestrates AI coding agents, regardless of stack, language, or cloud provider. The reference implementation (aider-relay) demonstrates it working before any spec is formally published.

## Alternatives Evaluated

### A2A (Google Agent-to-Agent Protocol)
- Handles task delegation (new task to a new agent); does not handle in-progress session continuation
- HTTP-based; requires both agents to be running HTTP services — not viable for subprocess-based agentic CLIs
- Could be complementary: A2A for fresh task dispatch; MTARP for continuation after exhaustion

### MCP (Model Context Protocol)
- Addresses inbound tool/resource access for a single agent; not inter-agent communication
- Orthogonal to MTARP — a MTARP-compliant agent may also be an MCP client

### OpenAI Assistants Threads
- Provides session continuity within OpenAI's platform; non-transferable to other providers
- Exactly the problem MTARP solves, but locked to one vendor

### Framework-specific handoff (LangGraph, CrewAI)
- Tightly coupled to the orchestration framework; not portable across projects
- MTARP is the protocol layer these frameworks could implement, making their handoffs interoperable

## Compliance Levels

| Level | Requirements | What it enables |
|---|---|---|
| **Minimal** | Write Phase 1 `session.json` on handoff; read it on startup | Basic continuation across any two providers |
| **Standard** | Phase 2 fields; `agent-card.json`; `handoff_reason` enum | Tier-aware delivery; structured progress tracking |
| **Full** | Phase 3 fields; health event schema; benchmark score | Pre-emptive switching; routing hints; verifiable handoff quality |

## Validation Requirements

A protocol that cannot be verified is not a protocol. Before MTARP v1.0 is declared stable:

1. **Continuation coherence test**: The same Phase 1 envelope produces coherent task continuation in at least two independent agents. The `--sim-exhaust-after` test mode in aider-relay is the reference validation harness.
2. **Handoff quality benchmark**: A RouterBench-style evaluation that scores whether the incoming agent continued the task correctly given the envelope. Without a score, "compliant" is not verifiable.
3. **Health event coverage**: At least two providers emit health events in the standard schema, enabling pre-emptive switching (not just reactive).
4. **Non-commit task handoff**: Validated fallback for tasks that produce no git commits (Q&A, planning, review), where git provides no context.

## Applicability

- ✅ Any project orchestrating more than one AI coding agent
- ✅ Cost-tiered routing architectures (local → subscription → frontier)
- ✅ CI pipelines with agentic steps subject to usage limits
- ✅ Team workflows where different engineers use different AI providers on shared codebases
- ❌ Single-provider single-session workflows — no handoff, no protocol needed
- ❌ Non-coding agentic workflows — git-first design assumes a code repository
