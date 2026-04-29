---
id: KB-2026-005
type: design-space
status: draft
created: 2026-04-27
updated: 2026-04-27
tags: [model-switching, auto-resume, usage-window, ux]
related: [KB-2026-002, KB-2026-004]
---

# Auto-Resume After Usage Window Reset

## Context

After switching from Provider A (exhausted) to Provider B (fallback), should aider-relay automatically switch back to Provider A when its usage window resets? This is a UX and complexity question with significant implementation implications.

## Problem Statement

Usage windows are time-bounded (Claude Pro: ~5 hours, ChatGPT Plus: ~3 hours). Once the window resets, Provider A is available again. Should we:
1. Switch back automatically
2. Stay on Provider B for the remainder of the task
3. Prompt the user and let them decide

## Options in the Space

### Option 1: Stay on Fallback (No Auto-Resume)

Once switched, stay on Provider B until the user explicitly switches back with `/model`.

- **Complexity**: Zero — no new polling or timer logic
- **UX**: Simple and predictable — user always knows which model is active
- **Risk**: User may forget they're on the fallback model; may accumulate costs on paid API if fallback uses API keys
- **Correctness**: Safe — no risk of double-switch during a response

### Option 2: Auto-Resume After Fixed Delay

Switch back to Provider A after a fixed timer (e.g. 5 hours for Claude Pro, 3 hours for GPT).

- **Complexity**: Medium — need a background timer thread
- **UX**: Seamless but potentially surprising mid-task
- **Risk**: Timer is inaccurate (window may reset sooner or later); switching mid-response is dangerous
- **Correctness**: Must only switch between user turns, never during a model response

### Option 3: Probe on Next Request

Before each request, probe Provider A with a minimal "health check" call. If it succeeds, switch back.

- **Complexity**: High — need probe logic, handle probe failures gracefully
- **UX**: Seamless if done correctly
- **Risk**: Probes consume tokens; probe may succeed but full request may still hit limits
- **Correctness**: Same inter-turn constraint applies

### Option 4: User-Prompted Resume

When the estimated reset time arrives, ask the user: "Provider A window may have reset. Switch back? [y/N]"

- **Complexity**: Low-medium — timer + IO prompt
- **UX**: Transparent and user-controlled
- **Risk**: Interrupts flow if user is in the middle of reading output
- **Correctness**: User-gated so no race conditions

## Design Space Map

| Option | Complexity | UX Clarity | Risk | Implementation Priority |
|--------|------------|------------|------|------------------------|
| 1: Stay on fallback | Minimal | High | Low | Ship first |
| 2: Auto-resume timer | Medium | Medium | Medium | Phase 2 |
| 3: Probe on request | High | High | Medium | Phase 3 |
| 4: User-prompted | Low-Medium | High | Low | Phase 2 |

## Pareto Frontier

- **Option 1** dominates for initial implementation (Gall's Law — simplest working system)
- **Option 4** is the best next step — low complexity, transparent, user-controlled
- **Option 3** is the eventual goal but should not be built until Options 1 and 4 are proven

## Convergence Strategy

Phase 1: Always stay on fallback (Option 1)
Phase 2: Add optional user-prompted resume with configurable timer (Option 4)
Phase 3: Optionally add probe-based resume (Option 3) if user demand exists

## Critical Unknown

**Does the provider include the reset time in the exhaustion error response?** (see KB-2026-002)

If yes: Options 2, 3, 4 all become much more accurate.
If no: We must use approximate fixed timers or user knowledge.

## Applicability

- ✅ Relevant to the long-running task UX design
- ✅ Determines whether background threads are needed (significant complexity)
- ❌ Not relevant to the basic "detect and switch" implementation
