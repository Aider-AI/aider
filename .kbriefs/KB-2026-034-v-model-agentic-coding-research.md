---
id: KB-2026-034
type: research
status: active
created: 2026-05-01
updated: 2026-05-01
tags: [v-model, agentic-coding, research, sdlc, verification, vacuity, traceability]
related: [KB-2026-033, KB-2026-031, KB-2026-030]
---

# V-Model in Agentic Coding: Research Landscape and Gap Analysis

## Purpose

Survey the research landscape at the intersection of agentic coding and the V-model.
Identify what exists, what is missing, and where the genuine research contribution lies.

---

## Research Landscape

### What papers exist

| Paper | Contribution | V-model alignment |
|---|---|---|
| A Survey on Code Generation with LLM-based Agents (arXiv:2508.00083) | Defines agentic coding as plan→code→test→debug loops; covers ChatDev, MetaGPT, CodeChain | Left side of V (SDLC coverage) — no paired verification |
| AI Agentic Programming: A Survey (arXiv:2508.11126) | Autonomous, iterative, tool-using systems; multi-step reasoning + feedback loops | Right side execution loop — no traceability back to requirements |
| LLM-Based Agentic Systems for SE (arXiv:2601.09822) | Agents across requirements/coding/testing/debugging | Very close to V decomposition but presented as pipeline, not paired structure |
| CodeCoR: Self-Reflective Multi-Agent (arXiv:2501.07811) | Prompt agent → coding agent → test agent → repair agent | Accidentally V-shaped (left: prompt→code; right: test→repair) — no formal traceability |
| Agentic Verification of Software Systems / AutoRocq (arXiv:2511.17330) | Formal verification loops via agents | Strongest right-side alignment — not connected to requirements |
| Towards Verified Code Reasoning by LLMs (arXiv:2509.26546) | Agent reasoning → formal representations → correctness verification | Right side, no requirements link |
| AIDev: AI Coding Agents on GitHub | ~900k agent-generated PRs; feature dev, debugging, testing at scale | Proto-agentic SDLC, no formal structure |

### The pattern

The field is converging on V-model-like structures **without naming or formalising it**.
Every paper covers parts of the V. None connects requirements to verification with
explicit traceability.

---

## The Core Gap

### What exists

- Agents covering the full SDLC (requirements → code → test → repair)
- Iterative feedback loops
- Multi-agent specialisation
- Increasing formal verification integration

### What is missing (almost entirely)

- **Explicit requirement ↔ test traceability**
- **Formal pairing of design decisions ↔ integration validation**
- **Vacuity detection** — requirements that are never meaningfully exercised
- **End-to-end correctness guarantees**
- **Auditability frameworks**

### The field's current answer

> "Agents can do the whole SDLC."

### The unanswered question

> "How do we prove the system satisfies its requirements?"

That is exactly the problem the V-model was invented to solve.

---

## The Core Insight (paper thesis)

**Test-passing ≠ requirement satisfaction.**

A payment system where:
- `test_payment_created` ✓
- `test_payment_approved` ✓
- `test_payment_executed` ✓

...can still violate:
- Same user approved and executed (separation of duties broken)
- Break-glass event not logged
- Post-break-glass approval allowed

The tests pass. The requirement is vacuous — it was never exercised.

Current agents optimise for "patch passes tests."
A V-model agentic system optimises for:

> requirement intent → design decision → implementation → verification evidence → traceable satisfaction

---

## KBPD Alignment

K-Briefs are already the left side of the V-model:

| V-model artifact | KBPD equivalent |
|---|---|
| Requirements | K-Brief objective + acceptance criteria |
| Design decisions | K-Brief analysis + decisions recorded |
| Formalized constraints | K-Brief open questions + constraint statements |
| Verification evidence | K-Brief status + related KB links |
| Traceability | KB ID cross-references |

**What KBPD currently lacks:** the right side. K-Briefs record design intent but do not
enforce it. There is no agent that checks whether the implementation satisfies the
K-Brief's acceptance criteria. The V-model agentic system is the right-side complement
to KBPD.

---

## Predicted Trajectory (from paper evidence)

| Horizon | What arrives |
|---|---|
| Now–1 year | More MetaGPT-style orchestration; better test/repair loops |
| 1–3 years | Formal verification + agent integration (already starting) |
| Breakthrough | A system encoding requirements formally, linking to tests/constraints, enforcing traceability, detecting vacuity |

That breakthrough is: **V-model + agentic execution + formal constraints**.

---

## Key Sources

- [A Survey on Code Generation with LLM-based Agents (arXiv:2508.00083)](https://arxiv.org/abs/2508.00083)
- [AI Agentic Programming: A Survey (arXiv:2508.11126)](https://arxiv.org/abs/2508.11126)
- [LLM-Based Agentic Systems for SE (arXiv:2601.09822)](https://arxiv.org/pdf/2601.09822)
- [CodeCoR: Self-Reflective Multi-Agent (arXiv:2501.07811)](https://arxiv.org/abs/2501.07811)
- [Agentic Verification of Software Systems (arXiv:2511.17330)](https://arxiv.org/abs/2511.17330)
- [Towards Verified Code Reasoning by LLMs (arXiv:2509.26546)](https://arxiv.org/abs/2509.26546)
