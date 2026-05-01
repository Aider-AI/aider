---
id: KB-2026-024
type: design-space
status: draft
created: 2026-04-30
updated: 2026-04-30
tags: [panel, consensus, multi-agent-debate, ensemble, mixture-of-agents, mtarp-extension]
related: [KB-2026-021, KB-2026-022, KB-2026-016, KB-2026-017, KB-2026-018]
---

# Panel of Experts / Consensus Patterns for Multi-Agent Systems

## Motivation

MTARP (KB-2026-021/022) was designed for sequential session continuation: one agent
exhausts, another picks up. But the same routing infrastructure could support a
fundamentally different pattern — running multiple agents **in parallel** on the same
problem and aggregating their outputs. This is the "board of experts" or "panel" pattern.

This KB surveys what has been built in this space and assesses what it would mean for
aider-relay.

---

## The Landscape

### 1. Multi-Agent Debate (MAD)

**Core paper:** Du et al. (2023), "Improving Factuality and Reasoning in Language Models
through Multiagent Debate" (ICML 2024). [arXiv:2305.14325]

Multiple model instances propose answers independently, then iteratively debate over
multiple rounds — presenting arguments, counter-arguments, and revising positions.
Works with only black-box model access. Significant gains on factual and reasoning tasks.

**Liang et al. (2024)** (EMNLP) introduced MAD specifically to break "Degeneration-of-Thought"
— the failure mode where a model becomes overconfident in a wrong answer and stops
updating. Heterogeneous agent roles (tit-for-tat debate with a judge moderator) help.

**Critical finding (2025):** "Debate or Vote: Which Yields Better Decisions?"
[arXiv:2508.17536] — majority voting alone accounts for most of the gains traditionally
attributed to debate. Pure multi-round debate provides limited additional benefit over
simple ensemble voting. This is the key calibration result: debate is expensive and mostly
re-discovers what voting already finds.

### 2. Mixture of Agents (MoA)

**Together AI, 2024.** [arXiv:2406.04692]

Layered architecture: N diverse LLMs (proposers) generate candidate responses; an
aggregator layer synthesizes all outputs into a refined response. Achieves 65.1% on
AlpacaEval 2.0, exceeding GPT-4 Omni (57.5%) using only open-source models.

**Mechanism distinction from debate:** MoA is feed-forward (proposers → aggregator, no
back-and-forth). Debate is iterative (agents respond to each other). MoA is more
practical for latency-sensitive pipelines; debate is better for hard reasoning tasks
where iteration matters.

**Limitation:** 2–4× inference cost and latency. Good for batch/offline use; poor for
real-time.

### 3. Self-Consistency (Ensemble over a Single Model)

**Wang et al. (ICLR 2023).** [arXiv:2203.11171]

Sample multiple diverse reasoning paths from the same prompt using the same model;
majority-vote the final answer. Gains: +17.9% GSM8K, +11.0% SVAMP. Cheapest ensemble
pattern — no heterogeneous models required, just temperature variation.

**Key insight:** This is the baseline that must be beaten before adding model diversity
or debate overhead.

### 4. Panel-of-Judges (Evaluation Pattern)

**ChatEval (2023)** [arXiv:2308.07201] — Multi-agent referee team where each agent has
a unique persona (different expertise domains). Agents discuss response quality before
consensus rating. Higher accuracy and human-alignment than single-judge evaluation.

**PoLL (Panel of LLM evaluators)** — 3+ diverse smaller models independently assess;
scores aggregated via max voting or average pooling. Reduces single-model bias.

**JudgeBench (ICLR 2025)** [arXiv:2410.12784] — Benchmark for judge quality on
challenging response pairs where crowdsourced human judgment is unreliable (factual
correctness matters more than preference).

Panel-of-judges is currently the most mature and practically deployed panel pattern —
used widely in LLM evaluation, less so in production reasoning.

### 5. Role-Based Heterogeneous Debate

**Adaptive Heterogeneous MAD (A-HMAD), 2025** [Springer]

Agents assigned distinct reasoning specialties: Verifier (fact-checking), Solver
(computation), Critic (adversarial). 4–6% absolute gains over standard homogeneous
debate on challenging benchmarks. Reaches unanimous agreement in 92% of arithmetic
problems.

**ReConcile Framework** — confidence-weighted voting with neutral moderator. Explicit
confidence weighting rather than equal voting power.

**Key insight:** Heterogeneous roles outperform identical debaters. The diversity must
be in the agent's function, not just its temperature.

### 6. Consensus vs. Diversity: The Core Tension

**2025 EMNLP finding:** Consensus-based heuristics converge on popular solutions and
amplify filtering of correct answers for harder problems. Disagreement-based strategies
(deliberately selecting diverse, low-confidence answers) often outperform consensus
approaches on hard tasks.

**Optimal Weight (OW) and Inverse Surprising Popularity (ISP)** [arXiv:2510.01499] —
algorithms that leverage second-order information (model correlations and confidence
patterns) to improve on simple majority voting. OW-L outperforms majority voting in
97.92% of test cases.

**Disagreement as signal** [arXiv:2604.03796] — Rather than treating disagreement as
noise to resolve, unanimous model agreement on hard problems often signals systematic
error, not correctness. A 4-category taxonomy: reasoning similarity × conclusion
agreement → genuine plurality vs. error pattern.

**Iterative Consensus Ensemble (ICE), 2025** — Multiple LLMs iteratively reason and
provide feedback over several cycles. Raises GPQA-diamond from 46.9% to 68.2%
(PhD-level reasoning benchmark, 45% relative gain). Best demonstrated result for hard
reasoning.

### 7. Anthropic: Collective Constitutional AI

**Anthropic (2023)** — Solicited ~1,000 public members to vote on constitutional rules
via Polis. 1,127 statements, 38,252 votes. Constitution includes only statements passing
consensus threshold across all opinion groups. Identified 2+ distinct opinion clusters
with genuinely conflicting priorities (collective good vs. individual liberty).

Relevant because it demonstrates that **some disagreements are not resolvable** by
consensus — they reflect genuine value pluralism. A panel system needs to represent this
rather than paper over it.

---

## Synthesis: What This Means for aider-relay / MTARP

### The sequential vs. parallel distinction

Current MTARP is sequential: Claude works → exhausts → Codex continues. The panel
pattern is parallel: Claude AND Codex (and possibly others) work on the same problem
simultaneously → outputs are aggregated by a synthesizer.

These are genuinely different use cases with different strengths:

| Pattern | When to use | aider-relay fit |
|---|---|---|
| Sequential (current MTARP) | Long-running coding tasks that need to continue past a usage limit | ✅ Primary use case |
| Panel / consensus | Ambiguous decisions, code review, architecture choices, risk assessment | 🔲 Extension |
| Panel / diversity | Creative exploration, generating multiple solution approaches | 🔲 Extension |
| Panel / judge | Evaluating the quality of a prior agent's output before switching | 🔲 Could integrate into MTARP handoff |

### The most practical panel pattern for aider-relay

Based on the research, the highest-value / lowest-complexity extension is:

**Pre-switch evaluation panel:** When primary provider exhausts, before handing off
to the fallback, route the handoff context to a lightweight panel (e.g., 2–3 completion
API models) to assess the state of the work:
- Is the prior provider's output complete or partial?
- Are there obvious errors or incomplete edits?
- What should the incoming provider prioritise?

This is a **judge panel** (cheapest pattern, most mature) inserted into the MTARP
handoff flow. It improves handoff quality without requiring parallel coding agents.

A full parallel coding panel (two coding agents simultaneously editing the same
codebase) introduces merge conflicts and coordination overhead that the research has
not solved for agentic file-editing tasks.

### What the research does NOT cover

The entire body of work above operates on **text generation** (reasoning, factual QA,
evaluation). None of it addresses:
- Parallel agents making file edits to a shared repository
- Coordinating agentic tool use (bash, file writes) across concurrent sessions
- Merging divergent git histories from parallel agent runs

This is an open gap. Parallel coding agents would need git branching + merge
coordination before panel patterns apply to agentic coding.

---

## Recommended next steps for aider-relay

**Phase 3 (natural extension):** Add a judge panel step to the MTARP handoff:

```python
# After primary exhausts, before handing off to fallback:
panel_verdict = await panel_judge(
    task=task,
    session=session,
    git_context=git_context(),
)
# panel_verdict: {"completeness": "partial", "issues": [...], "priority_for_next": "..."}
# Inject panel_verdict into the handoff_prompt for the incoming provider
```

This gives the incoming provider a structured assessment of what was done, not just the
raw git diff. The judge panel can use cheaper/faster models (Haiku, GPT-4o-mini) since
it's doing assessment, not coding.

**Not recommended yet:** Parallel coding agents running simultaneously on the same
repo — the coordination problem is unsolved and not required for the primary use case.

---

## Key Papers

| Paper | Year | Key result |
|---|---|---|
| Du et al. — Multiagent Debate | 2023 | MAD improves factuality; ICML 2024 |
| Wang et al. — Self-Consistency | 2022 | Majority voting over CoT paths; ICLR 2023 |
| ChatEval | 2023 | Role-based judge panel outperforms single judge |
| Together AI MoA | 2024 | Proposer→aggregator layers beat GPT-4o on benchmarks |
| Debate or Vote | 2024 | Voting explains most MAD gains |
| Beyond Majority Voting | 2024 | OW/ISP algorithms improve on voting |
| A-HMAD | 2025 | Role-based heterogeneous agents +4-6% on hard benchmarks |
| ICE | 2025 | Iterative ensemble: 46.9%→68.2% on PhD-level reasoning |
| Disagreement as Signal | 2025 | Unanimous agreement on hard tasks = error signal |

## Applicability

- ✅ Panel-of-judges pattern is practical now as a MTARP handoff quality step
- ✅ Self-consistency (same model, multiple samples) is the cheapest useful baseline
- ✅ MoA architecture is validated for offline/batch synthesis tasks
- ❌ Parallel coding agents on a shared repo — coordination problem unsolved
- ❌ Full multi-round debate — marginal gains over voting don't justify latency cost
