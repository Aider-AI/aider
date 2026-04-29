---
id: KB-2026-017
type: design-space
status: draft
created: 2026-04-29
updated: 2026-04-29
tags: [routing, multi-turn, session-policy, agentic, open-problem]
related: [KB-2026-007, KB-2026-016, KB-2026-006, KB-2026-010]
---

# Multi-Turn Routing Policy

## Context & Problem Statement

Every existing LLM router (RouteLLM, Routesplain, RouterBench baselines) makes **per-query, stateless decisions**. Multi-turn agentic routing — where the routing decision must account for session state built up across prior turns — is an explicitly open research problem with no validated prior art.

aider-relay's current design routes once at session start (or on exhaustion) and stays on that provider. A proactive router needs a policy for when and whether to re-route mid-session.

## The Decision

For each incoming user turn, the router can:

**A. Session lock-in:** Route the first turn, lock to that provider for the entire session. Switch only on exhaustion or explicit user command.
- Simple, predictable, no cross-turn complexity
- User may be on a slow/expensive provider for simple follow-up questions
- Current aider-relay behaviour

**B. Per-turn re-routing:** Re-classify every turn independently. Each turn picks the best provider for that message.
- Maximum efficiency — cheap turns go local, hard turns go frontier
- Context relay required on every provider change (expensive, lossy)
- No session continuity — the new provider doesn't know what happened before
- Breaks agentic provider session state (Claude Code session_id, Codex thread_id)

**C. Hybrid: lock-in with re-evaluation triggers**
Lock to a provider but re-evaluate routing at defined trigger points:
- End of a "logical task unit" (user types a new distinct task)
- Provider emits `allowed_warning` (approaching exhaustion — switch proactively)
- N turns elapsed on the current provider
- User explicitly requests a switch

**D. Tier-stable routing:** Route to a tier (agentic CLI, completion API, local), not a specific provider. Allow intra-tier switches (Claude Code ↔ Codex) freely, but cross-tier switches only on explicit triggers.

## Critical Constraint: Agentic Session State

Agentic CLI providers (Tier A) maintain server-side session state tied to a `session_id` / `thread_id`. **This state cannot be transferred to a different provider.** A per-turn re-routing policy that switches providers between turns loses all session state accumulated by the agentic session — effectively restarting the agent.

This is fundamentally different from completion API routing where the caller holds the message history and can replay it to any provider. The session state opacity of agentic CLIs makes Option B non-viable for Tier A providers.

## Implication for Architecture

For **Tier A (agentic CLI) providers**: session lock-in is mandatory. The router picks a provider at session start and stays unless exhausted.

For **Tier B (completion API) / Tier C (hybrid) providers**: per-turn or hybrid re-routing is viable because the relay holds the message history and can replay it.

This means the routing policy differs by tier:

```
Task arrives
    │
    ▼
Tier classifier
    │
    ├── Tier A → lock in, route on exhaustion only
    │
    └── Tier B/C → re-evaluate each turn (relay holds history)
```

## Design Space Map

| Option | Tier A viable? | Efficiency | Complexity | Recommended phase |
|---|---|---|---|---|
| A: Session lock-in | ✅ | Low | Minimal | Phase 1-2 (now) |
| B: Per-turn re-route | ❌ | High | High | Not for Tier A |
| C: Hybrid triggers | ✅ | Medium | Medium | Phase 3 |
| D: Tier-stable | ✅ | Medium | Low | Phase 2-3 |

## Convergence Strategy

**Phase 1-2 (now):** Session lock-in for all providers. Switch only on exhaustion.

**Phase 3:** Add trigger-based re-evaluation at logical task unit boundaries. Define "logical task unit" as: user sends a message not obviously continuing prior context (heuristic: no pronoun reference to prior output, or explicit new task phrasing).

**Phase 4:** Tier-stable routing. Route to tier at session start; allow intra-tier provider switching freely. Cross-tier switches only on explicit user request or full exhaustion of all providers in the tier.

## Open Questions

1. How do we detect "logical task unit" boundaries reliably without a model call? Rule-based heuristics (pronoun references, task keywords) or lightweight classifier?
2. For Tier B/C per-turn routing, what is the minimum message history that must be replayed to preserve conversational coherence?
3. When switching within Tier A (Claude Code → Codex on exhaustion), session state is fully lost. Is the git-only handoff (KB-2026-007) sufficient for the new agentic session to continue coherently? — **This is what the sim-exhaust-after test is designed to validate.**

## Applicability

- ✅ Blocks any proactive routing implementation
- ✅ Determines whether relay_loop can ever do per-turn routing for Tier A providers (answer: no)
- ✅ Must be resolved before KB-2026-016 Phase 3 routing is designed
