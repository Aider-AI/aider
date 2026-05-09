---
id: KB-2026-047
type: design-space
status: draft
created: 2026-05-06
updated: 2026-05-06
tags: [architecture, unified-access, subscription, api, provider, credential, routing]
related: [KB-2026-001, KB-2026-003, KB-2026-006, KB-2026-016, KB-2026-017, KB-2026-019, KB-2026-020, KB-2026-029]
---

# Unified Provider Access Model

## Context

aider-relay currently has two completely separate code paths for accessing LLMs:

1. **Relay path** (`aider-relay` CLI): `BaseProvider` → SDK/subprocess. Uses
   file-based credentials (`.claude/`, `.codex/`). Providers are agentic runtimes
   that manage their own codebase view. Session state is opaque.

2. **Aider path** (`aider` CLI): `Coder` → litellm → OpenAI/Anthropic APIs. Uses
   env var API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Completion-style calls
   where aider applies edits via SEARCH/REPLACE diffs. Message history is portable.

These paths share no authentication, no routing, and no UI. A user with a Claude Pro
subscription can run `aider-relay` but not `aider --model claude-sonnet-4-20250514` (no API
key). A user with an OpenAI API key can run `aider --model gpt-4o` but not
`aider-relay --primary codex` (no `.codex/` credential).

The project's goal is to leverage **consumer subscriptions** alongside traditional API
access. A unified access model is needed so the user gets the best available provider
without caring about the underlying access mechanism.

## Problem Statement

How should aider-relay present a single interface that transparently uses subscription
CLI providers, direct API providers, and local models — selecting based on availability,
capability, and cost?

## Design Space Dimensions

| Dimension | Description | Range |
|---|---|---|
| **Auth unification** | How credentials are discovered and managed | Per-path (now) → unified store |
| **Entry point** | How many CLIs the user must choose between | Two (now) → one |
| **Feature parity** | Interactive features available in unified mode | Minimal (relay) → rich (aider) |
| **Provider selection** | How the right provider is chosen | Manual flag → auto-detect |
| **Session model** | How state is managed across providers | Per-provider → unified envelope |

## Options in the Space

### Option A: Relay-first unification

Make `aider-relay` the single entry point. API providers accessed via `AiderProvider`
(KB-2026-029). Subscription providers via existing `ClaudeCodeProvider`/`CodexProvider`.
The relay loop handles all routing. Aider's `Coder` becomes a provider, not the entry
point.

- **How:** Add `--model gpt-4o` flag to `aider-relay`. When the model string isn't a
  known subscription provider, instantiate `AiderProvider(model)` as a relay provider.
- **Strengths:** Single CLI. Unified routing and MTARP for all providers. Subscription
  providers are first-class, not an afterthought.
- **Weaknesses:** Loses aider's rich interactive features (`/add`, `/drop`, `/undo`,
  `/lint`, `/test`, file picker, streaming token output). Relay's print-based UI is
  minimal. Double-wrapping overhead (relay → AiderProvider → Coder → litellm).
- **Evidence:** KB-2026-029 validates that `AiderProvider` works. KB-2026-037 shows
  relay UI is improving (heartbeat). But the feature gap with aider's CLI is large.

### Option B: Aider-first unification (litellm custom provider)

Keep aider's `Coder` as the primary interface. Add subscription providers as litellm
custom providers or local proxies that translate SDK calls into OpenAI-compatible
completion responses.

- **How:** Build a local proxy (e.g. FastAPI on localhost) that accepts
  `/v1/chat/completions`, forwards to Claude Code SDK, translates agentic tool-call
  results back into completion responses.
- **Strengths:** All aider features work. Single codebase. Users get the rich CLI/GUI.
- **Weaknesses:** KB-2026-003 **eliminated this option**. Agentic CLIs are not completion
  APIs — they manage files, run commands, maintain session state. Translating autonomous
  file edits into SEARCH/REPLACE blocks is an impedance mismatch that produces fragile,
  lossy results. The proxy must fake streaming, handle tool calls internally, and
  reconstruct a coherent completion response. Extremely complex and brittle.
- **Status:** DOMINATED by Option A and D. Do not pursue.

### Option C: Shared provider pool, dual entry points

Keep both `aider` and `aider-relay` CLIs. Unify at the credential and configuration
layer: a shared provider registry that both CLIs consult. Each CLI does what it does best.

- **How:** Shared config file (e.g. `.aider-relay/providers.yml`) listing available
  providers with their auth method. `aider` reads it for API models. `aider-relay` reads
  it for all models. Credential discovery is unified.
- **Strengths:** Each CLI remains focused. No architectural compromise. Shared config
  reduces confusion.
- **Weaknesses:** Two CLIs is confusing. User must know which to use when. No unified
  routing across subscription and API providers. Subscription providers are relay-only;
  API providers are aider-only (unless AiderProvider bridges them).

### Option D: Progressive unification via relay as orchestrator

Relay becomes the single orchestration layer that dispatches to the appropriate backend:
- For subscription providers: direct SDK/subprocess (current path)
- For API providers: `AiderProvider` wrapping `Coder` in-process (KB-2026-029)
- For local models: `AiderProvider("ollama/...")` (KB-2026-016 Phase 3)

Single CLI (`aider-relay`) with auto-detection: check available credentials, build the
provider pool, route accordingly.

- **How:** On startup, relay probes for available credentials:
  - `.claude/` exists → add `ClaudeCodeProvider` to pool
  - `.codex/` exists → add `CodexProvider` to pool
  - `OPENAI_API_KEY` set → add `AiderProvider("gpt-4o")` to pool
  - `ANTHROPIC_API_KEY` set → add `AiderProvider("claude-sonnet-4-20250514")` to pool
  - Ollama reachable → add `AiderProvider("ollama/...")` to pool
  The first available provider becomes primary; rest are fallbacks. User can override
  with `--primary` / `--fallback` flags.
- **Strengths:** Single entry point. Auto-detection means zero config for most users.
  Progressive — start with credential detection, add smart routing later (KB-2026-016).
  Subscription providers remain first-class agentic runtimes. API providers get full
  aider edit capabilities via `AiderProvider`.
- **Weaknesses:** Relay UI is still minimal compared to aider's CLI. Interactive features
  (`/add`, `/undo`) not available. `AiderProvider` has no streaming to relay (KB-2026-029:
  single text event per turn).
- **Mitigation:** Heartbeat (KB-2026-037) covers the silence gap. Interactive features
  can be added progressively to relay (KB-2026-041). Or relay can launch aider's CLI
  as the `AiderProvider` interface for API models, getting streaming for free.

## Design Space Map

| Option | Auth unified | Single CLI | Feature parity | Complexity | Recommended |
|---|---|---|---|---|---|
| A: Relay-first | ✅ | ✅ | Low (relay UI) | Low | Phase 2 |
| B: Aider-first proxy | ✅ | ✅ | High (aider UI) | Very high | ❌ Dominated |
| C: Dual CLIs | Partial | ❌ | High (each CLI) | Low | Not recommended |
| D: Progressive | ✅ | ✅ | Medium → High | Medium | ✅ Phase 2-4 |

## Dominated Solutions

- **Option B (Aider-first proxy):** Strictly dominated. KB-2026-003 eliminated the proxy
  approach. Impedance mismatch between agentic runtimes and completion APIs is
  fundamental, not incidental.

## Pareto Frontier

- **Option D** is the recommended path. It subsumes Option A (relay-first is the starting
  point of progressive unification) and avoids Option B's impedance mismatch.
- **Option C** is a valid interim state if the team wants to preserve aider's full CLI
  experience for API-only users while building relay's capabilities.

## Knowledge Gaps to Close

### Gap 1: Credential auto-detection (NEW)
What is the reliable, cross-platform way to detect available providers? File existence
checks (`.claude/`, `.codex/`) are simple but may give false positives (stale creds).
Env var checks (`OPENAI_API_KEY`) are straightforward. Ollama probe
(`http://localhost:11434/api/tags`) needs network access.

**Experiment:** Enumerate the exact checks for each provider and validate on Windows
(host) and Linux (devcontainer).

### Gap 2: AiderProvider readiness (from KB-2026-029)
Four open questions remain:
1. Does `Model("gpt-4o-mini")` raise at construction without an API key?
2. Is `asyncio.to_thread(coder.run)` safe given Coder's mutable state?
3. What exception types does litellm raise for rate limits?
4. Does `io.yes=True` suppress all confirmation prompts?

**Must close before:** AiderProvider can be a reliable API fallback in the relay pool.

### Gap 3: Provider preference ordering
When multiple providers are available, what is the default priority?
- Subscription first (flat cost, no per-token billing)?
- Highest capability first (Tier A before Tier B)?
- User-configured preference list?

**Relates to:** KB-2026-016 (routing approaches), KB-2026-017 (multi-turn policy).

### Gap 4: Relay interactive features (from KB-2026-041)
What subset of aider's interactive features (`/add`, `/drop`, `/undo`, `/test`, `/lint`)
should relay support? Is relay intentionally simpler (autonomous-first), or should it
converge toward aider's interactive experience?

### Gap 5: Cost model across tiers
Subscription providers have no per-token cost (flat monthly fee, usage windows). API
providers bill per token. Local models are free but slow. How does a unified cost
display/budget work? Is cost tracking even meaningful for subscription providers?

## Convergence Strategy

| Phase | Action | Closes gap |
|---|---|---|
| **Phase 2a** | Close Gap 2: validate AiderProvider open questions | Gap 2 |
| **Phase 2b** | Add credential auto-detection to relay startup | Gap 1 |
| **Phase 2c** | Add `--model` flag to relay: if model string given, use AiderProvider | Gap 1, 3 |
| **Phase 3** | Default preference ordering: subscription → API → local | Gap 3 |
| **Phase 4** | Add interactive commands to relay (`/add`, `/undo`) | Gap 4 |
| **Phase 5** | Unified cost tracking across tiers | Gap 5 |

## Applicability

- ✅ Determines the single-CLI vs dual-CLI decision
- ✅ Determines whether `AiderProvider` ships as a relay fallback
- ✅ Blocks credential auto-detection implementation
- ✅ Informs KB-2026-041 (aider UI integration) scope
- ❌ Does not change the existing provider interface (`BaseProvider`)
- ❌ Does not change MTARP session format
