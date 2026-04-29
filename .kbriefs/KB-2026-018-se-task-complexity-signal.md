---
id: KB-2026-018
type: design-space
status: draft
created: 2026-04-29
updated: 2026-04-29
tags: [routing, complexity-signal, task-classification, se-domain, local-llm]
related: [KB-2026-016, KB-2026-017, KB-2026-003]
---

# Software Engineering Task Complexity Signal

## Context & Problem Statement

The Phase 3 routing architecture (KB-2026-016) requires a task classifier that gates prompts to local LLMs vs. subscription CLIs vs. frontier APIs. General-purpose LLM routers (RouteLLM, RouterBench baselines) are trained on chat/QA datasets — they have no validated signal for the software engineering domain.

Routesplain (arXiv 2024) found that **routing performance degrades significantly when the task domain shifts from the training distribution** — a router trained on Chatbot Arena data cannot be assumed to generalise to SE-specific tasks. This is an explicit gap: what features of a coding prompt reliably predict the required capability tier?

## Known Complexity Signals (Surveyed)

### Prompt-level signals (cheap, no model call)

| Signal | Description | SE validity |
|---|---|---|
| Prompt token length | Longer prompts generally harder | Weak — a long spec for a trivial rename inflates this |
| Presence of task keywords | "refactor", "architect", "design" vs "fix typo", "rename" | Medium — brittle to phrasing variation |
| File count referenced | How many files are mentioned or implied | Medium — multi-file tasks more likely to need agentic tier |
| Code block presence | Prompt includes code paste | Low — pasted code could be trivial or complex |
| Question vs. command phrasing | "What does X do?" vs "Implement X" | Medium — questions may need less agentic capability |

### Repository-level signals (cheap, file system read)

| Signal | Description | SE validity |
|---|---|---|
| Repo size (LOC, file count) | Larger repos → more context needed | Low — applies to all tasks equally |
| Test coverage present | If tests exist, a change request needs test awareness | Low |
| Files recently modified | If many files changed recently, task likely cross-cutting | Medium |

### Model-derived signals (expensive, requires LLM call)

| Signal | Description | SE validity |
|---|---|---|
| Lightweight judge call | Small model scores prompt complexity 1-5 | High — but adds latency and cost for every turn |
| Embedding similarity to tier profiles | Cosine similarity to "simple refactor" vs "complex architecture" | High — Aurelio Labs semantic-router (KB-2026-016) |
| RouteLLM matrix factorisation | Win-rate classifier from Chatbot Arena data | Unknown for SE — trained on chat, not coding tasks |

## The Routesplain Gap

Routesplain (2024) introduced **domain-specific routing** to address this: instead of a universal complexity signal, route based on task taxonomy tags (auth, DB, API, UI). Their finding: taxonomy-conditioned routing outperforms prompt-length heuristics by 18–30% on SE benchmarks.

However, Routesplain targets completion API routing and has no implementation for agentic CLI dispatch. The taxonomy concept is extractable — tag the task type, map tags to tiers:

```
"rename variable" → tag: refactor → tier: local
"implement OAuth login" → tag: auth, api → tier: subscription_cli
"design event sourcing architecture" → tag: architecture → tier: frontier_api
```

No public taxonomy-to-tier mapping exists for the local/CLI/API provider spectrum.

## Design Space

### Option A: Prompt-length threshold (baseline)
Route to local if `len(prompt.split()) < 50`, else subscription CLI. No dependencies, sub-millisecond, but low accuracy for SE domain.

### Option B: Keyword taxonomy (Phase 3 target)
Define a keyword set for each tier:
- Local tier: "rename", "fix typo", "format", "explain what", "what does", "translate to"
- CLI tier: "implement", "refactor", "add feature", "write tests", "debug", "integrate"
- Frontier tier: "design", "architect", "plan", "evaluate trade-offs", "compare approaches"

Rule-based, no external calls, sub-millisecond. Brittle to phrasing but fast to iterate.

### Option C: Embedding similarity (Phase 4)
Pre-embed a set of exemplar prompts for each tier. At runtime, embed the incoming prompt and find nearest exemplar. Aurelio Labs `semantic-router` implements this with local embeddings (no API call required if using sentence-transformers).

### Option D: Cascade confidence signal (Phase 5)
Route to local LLM first; if output confidence (logprob entropy from llama.cpp) is below threshold, escalate to subscription CLI. High accuracy but doubles latency on escalated tasks.

## Convergence Strategy

**Phase 3:** Keyword taxonomy (Option B). Implement `TaskClassifier.classify(prompt) -> ProviderTier`. Fast, no dependencies, iterable without model retraining. Accuracy is secondary to having a working dispatch path.

**Phase 4:** Replace with embedding similarity (Option C) once there is enough session data to build tier-labelled training examples from actual relay usage.

**Phase 5:** Cascade with confidence (Option D) if local LLM accuracy is insufficient for medium-complexity tasks.

## Open Questions

1. Is there an existing SE-specific benchmark (HumanEval, SWE-Bench) routing dataset that provides a ground truth for prompt complexity → tier? RouterBench (KB-2026-016) evaluates routers on chat quality, not SE task success.
2. Can we collect tier-labelled examples automatically from relay sessions? If the user switches from local to CLI mid-session, that is implicit evidence the local tier was insufficient.
3. For the keyword taxonomy, what is the correct handling of mixed-signal prompts ("explain the OAuth flow and then implement it")? Split into two turns, or route to the highest tier required?

## Applicability

- ✅ Required before Phase 3 proactive routing is implemented
- ✅ Informs which features to extract in `TaskClassifier`
- ✅ Determines whether Routesplain taxonomy concept is adaptable without retraining
- ❌ RouteLLM classifier should not be used without SE-domain validation
