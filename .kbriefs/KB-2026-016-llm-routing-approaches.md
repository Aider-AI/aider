---
id: KB-2026-016
type: design-space
status: draft
created: 2026-04-29
updated: 2026-04-29
tags: [routing, llm-router, local-llm, cascade, semantic-routing, multi-provider]
related: [KB-2026-003, KB-2026-007, KB-2026-015]
---

# LLM Routing Approaches Design Space

## Context

aider-relay currently routes between Claude Code and Codex based purely on usage window exhaustion — a reactive, binary switch. The longer-term vision is a proactive router that selects the right provider for each task: local LLMs for cheap/fast tasks, subscription CLIs for complex coding tasks, frontier APIs as fallback. This K-Brief surveys leading routing approaches and their applicability.

## Critical Constraint

**No existing routing framework dispatches to agentic CLI providers.** All surveyed routers (RouteLLM, LiteLLM, OpenRouter, semantic-router) operate at the completion API boundary (`/v1/chat/completions`). aider-relay's routing layer sits one level above — classify the task first, then dispatch to the appropriate provider subprocess or API. The classification layer and the dispatch layer are separable concerns.

## Routing Approaches

### 1. RouteLLM (LMSys, Apache 2.0)

**Mechanism:** Trains a router on Chatbot Arena preference data using matrix factorisation. Computes a "strong model win rate" conditioned on the prompt; routes to the strong model if that probability exceeds a cost threshold.

**Signal:** Prompt content only — no latency, cost, or task-type taxonomy signal.

**Benchmarks:** 85% cost reduction on MT Bench, 45% on MMLU, maintaining 95% of GPT-4 quality.

**Fit for aider-relay:** The matrix factorisation classifier is worth extracting as a pre-trained complexity classifier even without the rest of RouteLLM's infrastructure. It runs inference independently of its serving framework and generalises beyond its GPT-4/Mixtral training pair. Use it to classify tasks before dispatching to a provider subprocess.

**Not applicable:** The full RouteLLM stack is a drop-in OpenAI client — it cannot dispatch to subprocess providers.

### 2. LiteLLM Router (MIT)

**Mechanism:** Six strategies: weighted shuffle (RPM/TPM-aware), latency-based, cost-based, least-busy, rate-limit-aware, semantic (embedding similarity to operator-defined utterances). Complexity Router uses rule-based scoring — zero API calls, sub-millisecond.

**Signal:** Throughput, latency, cost, semantic similarity, or rule-based complexity — configurable per strategy.

**Fit for aider-relay:** The **Complexity Router** concept is the most portable — rule-based, no external calls, sub-millisecond. Could classify "simple" vs "complex" coding tasks to gate local vs CLI dispatch without any API dependency. Full LiteLLM router cannot dispatch to subprocesses.

### 3. Cascade Routing

**Mechanism:** Cheap model first; escalate to expensive model if quality signal is insufficient. Quality signal is typically output token probability entropy (high entropy = uncertain = escalate). ETH Zurich paper (arXiv 2410.10347) achieves 97% of GPT-4 accuracy at 24% of cost.

**Signal:** Token probability logprobs from the cheap model's output.

**Problem for aider-relay:** Agentic providers don't expose logprobs. Cascade escalation signals must come from secondary checks (lightweight judge call, task-specific heuristics, or structured output validation).

**Fit for aider-relay:** Applicable if the cheap tier is a local LLM with logprob access (llama.cpp server exposes `logprobs` reliably), escalating to a subscription CLI. Latency impact is acceptable for coding tasks.

### 4. Semantic / Embedding-Based Routing

**Two distinct projects:**

**Aurelio Labs `semantic-router`** (open-source, pip-installable): builds capability profiles as embedding centroids, routes prompts by cosine similarity to the nearest profile. Uses OpenAI or Cohere encoders. Fast (no LLM call), but requires manual profile authoring.

**vLLM Semantic Router** (open-source, Red Hat): ModernBERT classifier extracting six signal types (domain, keyword, embedding, factual, feedback, preference). Targets inference cluster routing, not provider selection. Over-engineered for aider-relay's current scale.

**Fit for aider-relay:** Aurelio Labs library is the practical pick for Phase 3. Capability profiles for "simple autocomplete", "complex refactor", "debugging", "question-answering" could gate local → subscription CLI dispatch. Pip-installable, no server infrastructure.

### 5. Commercial Routers (OpenRouter, Martian, Not-Diamond, Unify AI)

None support agentic CLI dispatch. All are API proxies. **RouterBench** (Martian, open-source) is the standard evaluation harness — useful for benchmarking any custom router built for aider-relay.

### 6. Local LLM Integration

All major local serving options expose OpenAI-compatible `/v1/chat/completions`:

| Option | Port | Logprobs | Container-friendly | Notes |
|---|---|---|---|---|
| Ollama | 11434 | Limited | ✅ | Best default; stable API, good model selection |
| LM Studio | 1234 | Limited | ❌ (GUI) | Dev machine only |
| llama.cpp server | configurable | ✅ | ✅ | Best for cascade escalation signals |

**Olla** (open-source): thin router over multiple local Ollama endpoints with priority-based failover.

**Fit for aider-relay:** Ollama is the right default for a "cheap/fast local tier" — containerisable, stable API. llama.cpp server is the pick if logprob-based cascade escalation is needed.

## Recommended Architecture for Phase 3+

```
User task
    │
    ▼
Task Classifier (rule-based or RouteLLM matrix factorisation)
    │
    ├── "simple" ──────────► Local Ollama (cheap, fast)
    │                              │ low confidence? escalate
    ├── "medium" ───────────► Claude Code / Codex CLI (subscription)
    │
    └── "hard" / fallback ──► Frontier API (direct, metered)
```

The classifier sits outside the provider dispatch layer. Providers (local Ollama, Claude Code, Codex, API) each implement `BaseProvider` — the router just picks which one to instantiate.

## Convergence Strategy

| Phase | Routing logic | Signal | Notes |
|---|---|---|---|
| Now (Phase 1) | Reactive exhaustion switch | Usage window event | |
| Phase 2 | Proactive `allowed_warning` pre-switch + `error_kind` on `ProviderEvent` | Claude Code `RateLimitEvent` | `error_kind` required before any new provider joins pool (KB-2026-020) |
| Phase 3 | Rule-based complexity classifier; add Ollama as Tier B for **new sessions only** | Prompt length, task keywords | Tier B cannot continue Tier A sessions until Phase 4 validation (KB-2026-019) |
| Phase 4 | Semantic router (Aurelio Labs); validate Tier A → Tier B handoff | Embedding similarity to capability profiles | RouteLLM classifier not applicable without SE-domain validation (KB-2026-018) |
| Phase 5 | Cascade with local LLM | llama.cpp logprob confidence | |

## Applicability

- ✅ Phase 2: add `error_kind` to `ProviderEvent` before adding any new provider to the pool
- ✅ Phase 3+: implement rule-based task classifier before provider dispatch
- ✅ Phase 3+: add Ollama as a `LocalProvider(BaseProvider)` for **new sessions only** — no Tier A→B handoff until Phase 4 validated
- ✅ Phase 4+: validate cross-tier session portability (KB-2026-019) before enabling mid-session Tier B routing
- ✅ Phase 5+: cascade escalation using llama.cpp logprobs
- ✅ RouterBench for evaluating any custom router built here
- ❌ RouteLLM full stack — not applicable (completion API only)
- ❌ RouteLLM matrix factorisation classifier — SE-domain validity unvalidated (KB-2026-018)
- ❌ Commercial routers — not applicable (no subprocess dispatch)
