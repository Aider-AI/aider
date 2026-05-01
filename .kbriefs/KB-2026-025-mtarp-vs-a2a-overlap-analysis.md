---
id: KB-2026-025
type: critical-analysis
status: draft
created: 2026-04-30
updated: 2026-04-30
tags: [mtarp, a2a, protocol-comparison, overlap, redundancy, critical-analysis]
related: [KB-2026-021, KB-2026-022, KB-2026-023]
---

# MTARP vs. A2A: Overlap Analysis and Honest Assessment

## Purpose

KB-2026-021 claims MTARP addresses a gap that A2A does not cover. This KB stress-tests
that claim with the actual A2A technical specification. Conclusions inform whether
MTARP should be positioned as a standalone protocol, an A2A extension, or an
A2A-compatible complement.

---

## What A2A Actually Does (Technical Facts)

A2A v1.0 (production-stable, March 2026, Linux Foundation, 150+ org members) is a
wire protocol (JSON-RPC 2.0 / gRPC over HTTP/S) with Protocol Buffer canonical schema.
Key technical primitives:

**Agent Card** — machine-readable capability advertisement per agent. Fields: name,
description, supported interfaces, capabilities (streaming, push), skills (id, name,
description, input/output JSON Schema), security schemes. Returned via GetAgentCard RPC.

**Task** — stateful unit of work. Contains: unique `id`, optional `contextId` (groups
related tasks), `status` (9-state machine), `history[]` (full chronological conversation),
`artifacts[]` (immutable outputs accumulated during task), `metadata`. Tasks are
long-lived — they survive disconnections via push notification webhooks.

**Task state machine** — SUBMITTED → WORKING → COMPLETED/FAILED/CANCELED/REJECTED, with
interruption states INPUT_REQUIRED and AUTH_REQUIRED (resumes when client provides input
or auth). Terminal states do not transition.

**contextId** — optional string grouping identifier that an orchestrator can attach to
multiple tasks to indicate they are part of the same logical session. Agents SHOULD use
it to maintain conversational state.

**Streaming** — SSE for real-time streaming, webhook push notifications for disconnected
clients or very long-running tasks. Explicitly designed for tasks lasting hours or days.

---

## Where A2A Genuinely Overlaps With MTARP

### 1. Session continuation is possible over A2A

KB-2026-021 states: "Neither [A2A nor MCP] handles *session continuation*."

This is overstated. The following sequence IS session continuation implemented over A2A:

1. Orchestrator submits task T to Claude Code with `contextId="session-X"`
2. Claude Code works. Its outputs land in `artifacts[]`. Its reasoning is in `history[]`.
3. Claude Code hits usage limit → task reaches FAILED (or a custom terminal state)
4. Orchestrator submits a new task T' to Codex with the same `contextId="session-X"`,
   passes Claude's `history[]` and `artifacts[]` as context
5. Codex "continues" — it has the conversation history, the prior artifacts, the same
   context grouping

A2A does not provide this out-of-the-box in a single operation, but the primitives are
there. The claim that A2A "does not handle session continuation" is defensible only if
session continuation is defined as a *single RPC that transfers an in-flight task from
one agent to another*. Under that narrow definition, A2A does not have it. Under a
broader definition (a client orchestrator re-submitting with accumulated context), A2A
supports it.

### 2. Agent Card and MTARP's agent-card.json are the same concept

MTARP's planned `agent-card.json` (KB-2026-021):
```json
{
  "provider": "claude-code",
  "tier": "agentic_cli",
  "can_read_files": true,
  "handoff_requirements": { "delivery_mode": "pull" }
}
```

A2A's Agent Card:
```json
{
  "name": "claude-code",
  "capabilities": { "supportsStreaming": true },
  "skills": [{ "id": "code-edit", "description": "..." }],
  "defaultInputModes": ["text/plain"]
}
```

These solve the same problem: telling a router what a provider can do. MTARP's
`delivery_mode` (pull vs. push) maps directly to A2A's delivery semantics.
MTARP's tier model (agentic_cli, completion_api, hybrid) maps to A2A's capability flags.
**If MTARP publishes its own agent-card.json spec, it is reinventing A2A Agent Cards.**

### 3. Health event schema and A2A task states overlap

MTARP's planned health event schema:
```json
{
  "event_type": "health",
  "status": "exhausted | approaching_limit | transient_error | permanent_error"
}
```

A2A's task states: WORKING, FAILED, INPUT_REQUIRED. A2A's SSE streaming delivers
TaskStatusUpdateEvents with state transitions and messages in real time.

The mapping is imperfect but substantial: MTARP's `exhausted` ≈ A2A's FAILED with a
specific error message. MTARP's `approaching_limit` has no A2A equivalent (A2A has no
pre-exhaustion warning state). MTARP's `transient_error` ≈ A2A's FAILED with retry
semantics. MTARP's `permanent_error` ≈ A2A's FAILED terminal.

MTARP's health event schema adds the pre-exhaustion warning (`approaching_limit`) which
A2A lacks. That is a genuine gap in A2A. Everything else overlaps.

---

## Where MTARP Is Genuinely Distinct

### 1. Git as the universal substrate — A2A has no equivalent

A2A's `artifacts[]` can carry file contents, but A2A has no semantic understanding of
git. It cannot express "the agent committed three times; here is the SHA range; run
`git diff <diff_since>..<head>` to see what changed."

MTARP's `session.json` is **git-aware**: it records `git.head` (current commit SHA),
`git.branch`, `git.diff_since` (session-start SHA). This lets the incoming agent run
`git diff <diff_since>..HEAD` and reconstruct exactly what the outgoing agent did —
without the outgoing agent needing to narrate it.

This is MTARP's strongest genuine contribution. Git is lossless, objective, and
universally readable. No prior protocol treats git as a first-class session state carrier.

### 2. Exhaustion as a named, structured trigger

A2A has FAILED. It has no concept of *why* a task failed in a routing-relevant way.
MTARP's `handoff_reason` enum:

```
exhausted | escalate | deescalate | user_request | error
```

Each value changes what the incoming agent should do. `exhausted` means prior work is
committed and complete — continue. `escalate` means prior work may be incomplete — verify
first. `error` means the last committed state may not reflect the intent — audit before
proceeding.

A2A cannot express this distinction. An A2A task reaching FAILED is just failed —
the semantic reason is not structured. A router receiving an A2A FAILED event cannot
distinguish "Claude ran out of tokens but committed its work cleanly" from "Claude
crashed mid-edit and left files in an inconsistent state."

### 3. No A2A-compliant agents exist for CLI coding tools

A2A requires an HTTP server. Claude Code and Codex are CLI tools invoked as
subprocesses. Making them A2A agents requires wrapping them in HTTP servers with full
A2A protocol support — a significant engineering investment that does not exist today
and is not on either provider's roadmap.

MTARP's file-first approach (session.json in the repo) works with these tools exactly
as they are. The adoption cost is reading and writing a JSON file. This is the same
pragmatic argument the KB-2026-021 already makes and it is correct.

### 4. Provider tier model and handoff matrix

MTARP's three-tier model (agentic_cli, completion_api, hybrid) with its handoff matrix
determines *how* to deliver context to an incoming agent — not just *what* to deliver.
Tier A agents pull files themselves (inject task + git ref only). Tier B agents need
file contents injected. Tier C agents need tool definitions.

A2A's `defaultInputModes` and `skills` partially address this but not at the handoff
delivery level. A2A does not tell a router "for this agent, inject file contents rather
than a git reference." That tier-specific delivery logic is MTARP's.

---

## What MTARP Should Change Given A2A's Existence

### 1. Drop the standalone agent-card.json plan

MTARP should NOT publish its own agent-card.json spec. If A2A Agent Cards are adopted
(150+ organizations, Linux Foundation, v1.0 stable), defining a competing format
fragments the ecosystem.

**Recommendation:** MTARP's agent-card.json SHOULD be expressed as an A2A Agent Card
with an MTARP extension namespace. The `delivery_mode` and `tier` fields belong in an
A2A Agent Card extension:

```json
{
  "name": "claude-code",
  "extensions": ["https://mtarp.dev/v1/agent-extension"],
  "mtarp": {
    "tier": "agentic_cli",
    "handoff_requirements": { "delivery_mode": "pull" }
  }
}
```

This makes MTARP-compliant agents also A2A-compatible, not competing.

### 2. Express session.json as an A2A artifact

When a relay IS an A2A orchestrator (future state, not now), `session.json` should be
an A2A artifact carried in the task's `artifacts[]` array rather than a separate file.
This positions MTARP as a structured artifact schema on top of A2A transport, not a
competing transport.

### 3. Be precise about what "A2A does not cover" — it is narrower than claimed

The claim should be: "A2A does not natively support exhaustion-triggered continuation
with git-aware context." Not: "A2A does not handle session continuation." The former is
accurate. The latter is defensible only under a narrow definition and risks being
disproven as A2A evolves.

### 4. The health event schema should extend A2A's task states, not replace them

MTARP should map its health events to A2A task states with extensions, not define a
parallel state machine. The `approaching_limit` signal (no A2A equivalent) is the one
genuine addition.

---

## Honest Verdict

| Claim in KB-2026-021 | Assessment |
|---|---|
| "A2A handles task delegation, not session continuation" | **Overstated.** A2A's contextId + history + artifacts supports a form of continuation. The gap is narrower than claimed. |
| "No standard exists for in-flight session transfer" | **Defensible but imprecise.** True for single-RPC atomic transfer. Not true for orchestrator-driven re-submission. |
| "MTARP is distinct because git-first" | **Correct and strong.** No existing protocol is git-aware. This is the genuine contribution. |
| "MTARP is distinct because exhaustion trigger taxonomy" | **Correct.** A2A FAILED carries no routing-relevant semantic. |
| "MTARP needs its own agent-card.json" | **Wrong.** A2A Agent Cards with MTARP extension namespace is the right approach. |
| "File-first = no infrastructure required" | **Correct and strong.** The pragmatic advantage is real. |
| "A2A, MCP, OpenAI threads, LangGraph don't solve this" | **Substantially correct** for the specific git-aware coding agent continuation case. |

### What MTARP is

MTARP is a **semantic layer on top of (or beside) A2A**, not a competing transport
protocol. Its genuine contributions are:

1. Git as a first-class session state carrier
2. Exhaustion trigger taxonomy as a routing signal
3. Provider tier model governing how context is delivered
4. File-first adoption (no HTTP server required for current CLI providers)

### What MTARP is not

MTARP is not solving the inter-agent communication problem from scratch. A2A has solved
the transport layer. MTARP's work is in the application layer above it — specifically
for the coding-agent domain where git is the ground truth and CLI tools are the agents.

### The risk to watch

A2A v1.x could add:
- An `EXHAUSTED` task state (distinct from FAILED, with retry semantics)
- A `git://` artifact type with commit-SHA awareness
- A handoff extension for continuation with prior-agent context

If A2A adds these, MTARP's differentiation shrinks significantly. MTARP should move
toward positioning itself as an A2A extension spec (not a separate protocol) before A2A
absorbs the gap organically.

---

## Recommended Action

1. **Rewrite KB-2026-021's A2A comparison** to be precise about the narrow gap rather
   than the broad claim.
2. **Adopt A2A Agent Card format** with MTARP extension namespace for agent-card.json.
3. **Frame MTARP as a domain-specific extension** of A2A for git-based coding agents,
   not a competing general protocol.
4. **Contribute the `approaching_limit` health signal** to A2A as a proposed extension
   — it addresses a genuine gap and is valuable to any A2A implementation that routes
   based on provider capacity.
5. **Monitor A2A v1.1 roadmap** for exhaustion/continuation features that may absorb
   MTARP's unique claims.
