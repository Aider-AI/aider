---
id: KB-2026-020
type: design-space
status: draft
created: 2026-04-29
updated: 2026-04-29
tags: [routing, provider-health, availability, fallback-policy, local-llm, error-handling]
related: [KB-2026-016, KB-2026-017, KB-2026-002, KB-2026-010]
---

# Provider Health and Availability

## Context & Problem Statement

The current relay_loop handles one failure mode: **exhaustion** (usage window depleted). The routing architecture in KB-2026-016 adds two more provider types — local LLMs (Tier B, Ollama) and frontier APIs (Tier B/C, direct API) — each with distinct availability failure modes.

**Exhaustion is not the only reason a provider is unavailable.** A complete routing policy needs to distinguish:
- Exhaustion (temporary, time-bounded, recoverable)
- Process/network error (transient, may recover immediately on retry)
- Provider not installed / not running (hard failure, no automatic recovery)
- Rate limit (token-per-minute, not usage window — recoverable with backoff)
- Authentication failure (credential issue — not recoverable without user action)

The current code makes no distinction between these. All non-success events from `run_turn()` that aren't `"exhausted"` are printed as errors and the relay continues to wait for user input. A multi-provider routing layer needs a health model.

## Failure Mode Taxonomy

### Tier A — Agentic CLI (Claude Code, Codex)

| Failure | Signal | Recovery |
|---|---|---|
| Usage window exhausted | `RateLimitEvent(status="rejected")` / `exhausted` event | Wait for reset_at timestamp |
| Approaching limit | `RateLimitEvent(status="allowed_warning")` | Proactive switch (Phase 2) |
| Process crash | Subprocess non-zero exit, no events | Retry once; if fails, mark unavailable |
| Not installed | `FileNotFoundError` on subprocess | Mark permanently unavailable; no retry |
| Auth failure | Subprocess exits with auth error message | Mark permanently unavailable; surface to user |

### Tier B — Completion API (Ollama, llama.cpp server)

| Failure | Signal | Recovery |
|---|---|---|
| Server not running | `ConnectionRefusedError` on HTTP call | Mark temporarily unavailable; retry on next task |
| Model not pulled | 404 from Ollama API | Mark unavailable for this model; surface to user |
| Context overflow | 400/413 from Ollama API | Retry with truncated context |
| Rate limit (TPM) | 429 HTTP response | Backoff with retry |
| OOM (model too large) | Server crash mid-stream | Mark temporarily unavailable |

### Tier B/C — Remote API (OpenAI, Anthropic direct)

| Failure | Signal | Recovery |
|---|---|---|
| Rate limit (RPM/TPM) | 429 + `retry-after` header | Backoff |
| Quota exhausted (billing) | 429 with `insufficient_quota` body | Mark permanently unavailable; surface to user |
| API key invalid | 401 | Mark permanently unavailable; surface to user |
| Service outage | 5xx | Exponential backoff; escalate to next provider |

## Current State

`ProviderEvent` has `type: "error"` but the relay loop does not act on it — it just prints the content and loops back for user input. There is no concept of provider health state, no retry logic, no permanent unavailability marking.

`BaseProvider` has no `is_available()` method or health check mechanism.

## Design Space

### Option A: Fail-fast (current + minimal improvement)
On any non-exhaustion error, print the error and surface to user. No automatic recovery. Simple, predictable. User must intervene on any failure.

### Option B: Health state machine per provider
Each provider has a health state: `healthy | degraded | exhausted | unavailable`.

```
healthy     → normal operation
degraded    → transient errors; retry with backoff
exhausted   → usage window depleted; recover at reset_at
unavailable → permanent failure (not installed, auth failure); requires user action
```

State transitions driven by `ProviderEvent` type and error content. Router skips providers not in `healthy` or `degraded` state when selecting the next dispatch target.

- Completeness: High
- Complexity: Medium — requires state machine per provider instance
- Risk: Incorrect classification of transient vs. permanent errors

### Option C: Health check probe
Before routing to a provider, issue a lightweight probe (e.g., `echo "ping"` to local Ollama, a 1-token completion to the API). Route to the provider only if the probe succeeds.

- Completeness: Medium — probes can pass but the actual request can still fail
- Latency: Adds one round trip per probe per turn
- Not viable for Tier A CLIs (probes are full sessions)

### Option D: Circuit breaker pattern
After N consecutive errors, open the circuit for provider P — stop routing to it for T seconds. After T seconds, allow one probe request. If it succeeds, close the circuit (resume routing). Standard distributed systems pattern.

- Completeness: High for transient failures
- Complexity: Medium — well-understood pattern with libraries (e.g., `pybreaker`)
- Does not distinguish permanent from transient failures

## Recommended Architecture

**Phase 2:** Extend `ProviderEvent` to include an `error_kind` field:

```python
@dataclass
class ProviderEvent:
    type: str  # "text" | "exhausted" | "error" | "done"
    content: str = ""
    reset_at: str | None = None
    session_id: str | None = None
    error_kind: str | None = None  # NEW: "transient" | "permanent" | "rate_limit"
```

Each provider implementation classifies errors into these kinds. The relay loop acts on `error_kind`:
- `transient` → retry once, then switch provider
- `rate_limit` → backoff with `reset_at` hint, then retry
- `permanent` → mark provider unavailable, switch, surface to user

**Phase 3:** Add Option B health state machine. Simple three-state model: `healthy | exhausted | unavailable`. Exhausted providers are re-evaluated at `reset_at`; unavailable providers require user intervention.

**Phase 4:** Circuit breaker (Option D) for remote API providers where transient 5xx errors are expected under load.

## Availability vs. Exhaustion Distinction

The most important distinction for routing: **exhaustion** means "unavailable until a known future time" — the router should preemptively switch before hitting the limit (Phase 2 `allowed_warning` signal). **Error** means "unavailable for unknown duration" — the router must decide whether to retry or switch.

This distinction is not captured in the current `ProviderEvent.type` taxonomy (only `"exhausted"` vs `"error"` with no sub-classification).

## Open Questions

1. For Ollama, is `ConnectionRefusedError` always a "not running" state, or can it transiently fail during model load? Need to test Ollama startup/loading behaviour.
2. For Claude Code SDK, does `RateLimitEvent(status="rejected")` cover all exhaustion cases, or can the subprocess exit non-zero for quota reasons without emitting this event?
3. What is the user-visible UX for permanent unavailability? The relay should surface a clear message rather than looping indefinitely on failed provider switches.

## Applicability

- ✅ `error_kind` field on `ProviderEvent` ships in **Phase 2** alongside `allowed_warning` pre-switch — required before any new provider joins the pool (KB-2026-016 decision)
- ✅ Health state machine (`healthy | exhausted | unavailable`) is a Phase 3 prerequisite for multi-provider pool management
- ❌ Circuit breaker is Phase 4+ — do not add prematurely for a two-provider system
