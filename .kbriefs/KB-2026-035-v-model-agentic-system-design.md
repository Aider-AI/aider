---
id: KB-2026-035
type: design
status: active
created: 2026-05-01
updated: 2026-05-01
tags: [v-model, agentic-coding, system-design, cli, schema, open-source-strategy, benchmarks, vacuity]
related: [KB-2026-034, KB-2026-033, KB-2026-030]
---

# V-Model Agentic System: Architecture, Design, and Strategy

## Purpose

Define the system architecture, V1 schema, CLI design, evaluation approach, and
open/closed source strategy for a V-model agentic software engineering tool.

---

## Paper Thesis

**Title:** "Agentic V-Model Software Engineering: Traceable Requirements-to-Code
Generation with Verification-Guided Repair"

**Core claim:** Current coding agents optimise for "patch passes tests." A V-model
agentic system should optimise for requirement intent → design decision → implementation
→ verification evidence → traceable satisfaction. This is a stronger framing for
enterprise and regulated contexts than SWE-bench-style issue fixing.

**Stronger alternative framing (recommended):**
> "We implemented a CLI-based V-model agentic system and demonstrate that standard
> coding agents systematically miss requirement violations that our system detects
> and repairs."

**Killer experiment:** Use tasks where *all agents pass functional tests* — then show
which systems still violate the underlying requirement. That is the paper.

---

## System Architecture

### Left side: specification agents

| Agent | Role |
|---|---|
| Requirements agent | Converts stakeholder intent into structured requirements |
| Formalization agent | Converts requirements into constraints, invariants, acceptance criteria, temporal properties, security policies |
| Architecture/design agent | Component design, interfaces, data model, trust boundaries, failure modes |
| Test-design agent | Generates unit, integration, acceptance, property-based, negative tests **before coding** |

### Bottom: implementation agent

| Agent | Role |
|---|---|
| Coding agent | Implements under constraints; receives paired test suite before starting |

### Right side: verification agents

| Agent | Role |
|---|---|
| Unit verification agent | Detailed design ↔ unit tests |
| Integration verification agent | Architecture ↔ integration behaviour |
| Acceptance verification agent | Requirements ↔ acceptance tests |
| Constraint/formal verification agent | Invariants, temporal obligations, safety/security constraints |
| Traceability auditor | Evidence: requirement → design → code diff → test/constraint → result |

### The research contribution

Not "we made another coding agent." The contribution is:

> A V-model control structure for agentic software engineering that prevents agents from
> treating test success as equivalent to requirement satisfaction.

---

## Retrospective V-Model Reconstruction (stronger thesis)

For existing codebases — which is most enterprise reality — the more powerful framing is
**back-construction**:

```
Existing messy codebase
  ↓ Agentic reverse engineering
  ↓
Recovered requirements
Recovered design assumptions
Recovered invariants
Recovered architecture
Recovered test intent
Recovered verification gaps
  ↓
V-model asset graph
  ↓
Targeted repair, modernisation, audit, compliance, migration
```

**One-line product vision:**
> "Turn any repo into a traceable, test-driven, requirement-aware system — without rewriting it."

**Thesis statement:**
> Software entropy accumulates when code, requirements, tests, architecture, and
> rationale drift apart. Agentic V-model reconstruction reduces entropy by recovering,
> aligning, and verifying those artifacts.

**Best title direction:**
> "Reducing Software Entropy through Agentic Reconstruction of V-Model Artifacts"

---

## Evaluation Design (three layers)

### Layer 1: Standard coding-agent benchmarks (external credibility)

| Benchmark | Purpose |
|---|---|
| SWE-bench Verified | Patch success rate on real GitHub issues; baseline credibility |
| Multi-SWE-bench | Polyglot relevance (not Python-only) |
| SWE-bench Pro / SWE-MERA | Harder, contamination-resistant tasks from 2024–2025 |

Metrics: patch success rate, cost, iterations, time, regression rate.
**This is not enough on its own.**

### Layer 2: V-model traceability benchmark (the actual contribution)

Custom benchmark where each task includes:

| Artifact | Example |
|---|---|
| Natural-language requirement | "A payment may not be executed by its approver." |
| Design expectation | Role separation, event logging, authorisation boundary |
| Implementation target | Small service/repo |
| Hidden bug traps | Tests pass while requirement is violated |
| Verification oracle | Invariant, temporal constraint, property test, trace check |
| Expected evidence | Requirement → test → code trace |

Metrics:
- **Requirement satisfaction rate** — did the final system satisfy the requirement?
- **Test pass vs requirement pass divergence** — how often do tests pass while constraints fail?
- **Vacuity detection rate** — did the system notice a requirement was never exercised?
- **Trace completeness** — can every requirement be linked to design, code, verification?
- **Trace correctness** — are the links real, or hallucinated?
- **Repair quality** — does the agent fix the violation without breaking existing behaviour?

### Layer 3: Ablation study

| System | Description |
|---|---|
| Baseline coding agent | Issue → code → tests |
| Test-first agent | Issue → tests → code |
| Multi-agent SDLC agent | Requirements/design/code/test agents |
| V-model agentic system | Paired artifacts + traceability + constraints + verification repair |
| V-model without formal constraints | Tests only |
| V-model without trace auditor | No evidence enforcement |
| V-model without vacuity detection | Constraints exist but unexercised obligations missed |

Expected finding: the V-model agent may not always beat baseline on raw SWE-bench pass
rate, but should beat it on hidden requirement satisfaction, vacuity detection,
traceability, and safe repair.

### First 3 benchmark tasks (build these now)

1. **Hidden invariant violation** — tests pass; same user approves and executes payment
2. **Missing audit log** — system works; compliance requirement violated
3. **Vacuous requirement** — requirement exists; condition never triggered

---

## Open / Closed Source Strategy

### Open (drives adoption)

| Component | Rationale |
|---|---|
| CLI + agent routing framework | Becomes standard surface area; aligns with polyglot/devcontainer ecosystem |
| Plugin model (add agents) | Community can extend; you control the core |
| V-model schema / DSL | If this becomes a de facto standard ("OpenAPI for agentic SDLC") you win long-term |
| Benchmark dataset | Credibility engine; enables citations, community contributions, dataset paper |

### Closed (moat)

| Component | Rationale |
|---|---|
| Smart reconstruction intelligence | The secret sauce for back-constructing requirements/design/invariants from code |
| Advanced formal verification | Vacuity detection, temporal reasoning, correctness guarantees |
| Enterprise features | Compliance reports, audit trails, SLA enforcement |

### Rollout phases

| Phase | Open | Closed |
|---|---|---|
| 1 (now) | CLI shell, basic routing, Aider wrapper | Smart reconstruction, advanced verification |
| 2 | Benchmark dataset; early paper (ICSE workshop) | Best-performing reconstruction models |
| 3 | — | Enterprise compliance/audit features |

---

## V1 Schema (minimal, adoptable)

```yaml
requirements:
  - id: R1
    description: Payment must not be executed by its approver
    acceptance:
      - executor_id != approver_id

design:
  - id: D1
    component: PaymentService
    decisions:
      - enforce role separation at execution

code:
  - id: C1
    path: payment_service.py
    symbols:
      - execute_payment

tests:
  - id: T1
    path: test_payment.py
    cases:
      - test_executor_not_approver

constraints:
  - id: CSTR1
    type: invariant
    expression: approver_id != executor_id

trace:
  - requirement: R1
    design: D1
    code: C1
    tests: [T1]
    constraints: [CSTR1]
```

### Key design decisions

- **Tests ≠ constraints** — tests are executable examples; constraints are always-true
  rules. This is where the verification moat plugs in.
- **Trace is explicit (not inferred)** — make users declare trace; auto-inference comes
  later.
- **IDs are first-class** — everything references IDs; enables graph building, CLI
  queries, validation.

### V1 validation rules (implement immediately)

- Every requirement must have ≥1 test OR constraint
- Every test must map to a requirement
- Orphan code flagged
- Orphan requirements flagged

---

## CLI Design (V1)

```bash
vm init                          # creates .vmodel/model.yaml
vm req add "..."                 # adds requirement, assigns ID
vm test generate R1              # LLM generates tests, updates schema
vm run                           # plan → test → aider → test → report
vm check                         # health: orphans, untested requirements, vacuity
vm trace R1                      # requirement → design → code → tests → constraints
vm benchmark run swe-bench       # standard benchmark
vm benchmark run vmodel-bench    # V-model traceability benchmark
vm explain payment_service.py    # "this file implements R1; missing: negative test"
```

### `vm check` output (high value, build early)

```
✔ R1 has tests
⚠ R2 has no tests
⚠ 15% of code not linked to any requirement
⚠ constraint CSTR2 never exercised
```

### `vm explain` (killer UX feature)

```
vm explain payment_service.py
→ This file implements:
    R1: Payment must not be executed by its approver
  Missing:
    No constraint enforcement detected
    No test covering negative case
```

---

## Alignment with aider-relay

aider-relay's autonomous multi-provider loop (KB-2026-030) is the execution substrate.
The V-model agentic system is the control structure that runs *on top of* that substrate:

- KBPD K-Briefs → left side of V (requirements, design decisions, acceptance criteria)
- aider-relay relay_loop → bottom of V (implementation, provider cycling)
- V-model verification agents → right side (validation, traceability audit)

This is not a competing design — it is the discipline layer that makes aider-relay's
autonomous mode produce auditable, requirement-satisfying software rather than
test-passing patches.

---

## Related

- KB-2026-034: Research landscape and gap analysis
- KB-2026-033: KBPD + Karpathy wiki + Graphify synthesis
- KB-2026-030: aider-relay autonomous mode implementation
