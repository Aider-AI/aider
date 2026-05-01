---
id: KB-2026-036
type: synthesis+gaps
status: active
created: 2026-05-01
updated: 2026-05-01
tags: [system-of-systems, multi-repo, v-model, kbpd, graphify, mtarp, traceability, vacuity, enterprise]
related: [KB-2026-035, KB-2026-034, KB-2026-033, KB-2026-026]
---

# System-of-Systems: Applying the Stack at Multi-Repo Scale

## Purpose

Reason through how the KBPD + V-model + Graphify/Karpathy wiki stack applies when
the unit of concern is a capability or business requirement that spans multiple repos
and teams — and identify the knowledge gaps that must be closed before building.

---

## The Core Problem

A repo is not a system. A system is not a system of systems.

A requirement like:
> "No payment may be executed without a logged approval by a different user."

...spans at minimum: auth-service, payment-service, audit-service,
notification-service. Every repo can have green tests while the system-level
requirement is violated. No single team owns the failure. No current agentic tool
detects it.

This is the vacuity problem (KB-2026-034) at a higher level — and it is the most
expensive class of production failure precisely because it is nobody's unit test.

---

## Unit of Analysis Mismatch

| Level | Unit | Who owns it |
|---|---|---|
| Component | Class / module | Developer |
| System | Repo / service | Team |
| System of systems | Capability / business requirement | No one (the gap) |

Current agentic tools operate at component or system level. Requirements, compliance
obligations, and emergent behaviours live at SoS level. The mismatch is structural,
not a tooling shortfall — no tool addresses this layer.

---

## How the Stack Scales

### KBPD K-Brief hierarchy

K-Briefs form a natural three-tier hierarchy that mirrors the V-model nesting:

| Tier | Scope | Example |
|---|---|---|
| Component K-Brief | Within one repo | "Why does PaymentService use optimistic locking?" |
| System K-Brief | One service boundary | "Auth service token expiry assumptions" |
| Capability K-Brief | Cross-repo, cross-team | "Separation of duties across approval/execution flow" |

A capability K-Brief references multiple system K-Briefs. A system K-Brief references
component K-Briefs. The cross-repo lint gap (KB-2026-033) is most critical here: a
capability K-Brief's constraint can be silently contradicted by a system K-Brief in a
different team's repo.

### V-model nested structure

The V-model was designed for nested systems (aerospace/defence SoS engineering). Each
level has its own V; there is a meta-V at SoS level:

```
SoS level:    Capability requirements ←————————→ SoS integration tests
               ↓                                        ↑
System level: API / event contracts ←—————→ Contract tests (Pact, AsyncAPI)
               ↓                                        ↑
Repo level:   Implementation ←——————————→ Unit + integration tests
```

**Key insight:** At SoS level, the "implementation" the left side produces is the
*interface contract* (OpenAPI spec, AsyncAPI schema, Protobuf definition), not code.
Code is one level down. The right side's verification tool is contract testing, not
unit testing.

### Graphify / Karpathy wiki at SoS scale

| Within a repo | Across repos (SoS) |
|---|---|
| God nodes = classes, modules | God nodes = integration points, shared event schemas |
| Edges = import/call graph (AST) | Edges = API contracts, event topics, shared databases, trust boundaries |
| Source = code | Source = OpenAPI specs, AsyncAPI schemas, Protobuf definitions |
| GRAPH_REPORT.md per repo | Meta GRAPH_REPORT.md per system / capability |

A SoS Graphify pass would not run Tree-sitter over code — it would ingest API
contract files, event schemas, and infrastructure-as-code to build the integration
surface graph. The god nodes of that graph are the system's actual failure surface.

### MTARP at SoS scale

MTARP (KB-2026-026) currently carries single-repo session context across provider
handoffs. At SoS level, the handoff context needs to include which system-level
requirement the current task is contributing to — so an agent resuming work on
payment-service knows it is implementing cross-service SoD requirement R1, not an
isolated fix.

This requires a protocol extension: a `system_requirement_ref` field in the MTARP
session envelope that names the capability K-Brief and the cross-repo trace it belongs
to.

---

## Proposed SoS Schema (V1 sketch)

A `system.yaml` at a meta-repo or platform-repo level:

```yaml
system: payment-platform

components:
  - id: auth-service
    repo: github.com/org/auth-service
    kbrief: KB-AUTH-001
  - id: payment-service
    repo: github.com/org/payment-service
    kbrief: KB-PAY-003
  - id: audit-service
    repo: github.com/org/audit-service

integration-points:
  - id: IP1
    type: api
    provider: auth-service
    consumer: payment-service
    contract: contracts/auth-payment.openapi.yaml
  - id: IP2
    type: event
    producer: payment-service
    topic: payment.executed
    schema: schemas/payment-executed.asyncapi.yaml
    consumer: audit-service

capability-requirements:
  - id: CR1
    description: No payment may be executed without a logged approval by a different user
    spans: [auth-service, payment-service, audit-service]
    constraints:
      - approver_id != executor_id
      - audit-service receives payment.executed within 5s
    verification: tests/sos/test_sod_payment.py

trace:
  - requirement: CR1
    integration-points: [IP1, IP2]
    system-kbriefs: [KB-AUTH-001, KB-PAY-003]
    status: unverified
```

---

## Knowledge Gaps

These must be answered before building at SoS scale. Each gap is a candidate K-Brief.

### GAP-1: Does any current tool trace system-level requirements across repos?

**What we believe:** No tool does this. Contract testing tools (Pact) verify interface
compatibility but are not connected to business requirements. OpenTelemetry / distributed
tracing captures runtime behaviour but is not requirement-aware.

**What we need to know:** Is there tooling — commercial or open — that holds
cross-repo requirements and traces them to per-repo tests? DORA metrics, dependency
management tools (Renovate, Dependabot), platform engineering tools (Backstage)?

**Why it matters:** If something exists, we build on it. If nothing exists, this is the
product gap.

**How to answer:** Survey Backstage plugin ecosystem, contract testing landscape (Pact,
Spring Cloud Contract, OpenAPI spec validation), and platform engineering tooling.

---

### GAP-2: How do contract testing tools relate to requirements today?

**What we believe:** Contract testing (Pact et al.) verifies that a provider's API
satisfies a consumer's expectations — but the "expectation" is defined by the consumer
team's test, not by a business requirement. The link from requirement to contract to test
is manual and usually absent.

**What we need to know:** Is there a pattern in the industry for requirement-linked
contract tests? Has any team formalised "CR1 → contract test" traceability?

**Why it matters:** Contract testing is the natural right-side tool at SoS level. If
it can be requirement-linked, we have the verification layer. If not, we need to build
the bridge.

**How to answer:** Review Pact documentation, PactFlow (enterprise Pact), and academic
literature on requirement-driven contract testing.

---

### GAP-3: What is the right governance model for cross-team capability K-Briefs?

**What we believe:** A capability K-Brief spans multiple teams' repos. No single team
owns it. In practice this means it is nobody's responsibility — which is why the
problem exists in the first place.

**What we need to know:** How do large orgs (with platform teams, enabling teams,
stream-aligned teams — Skeleton/Pais Team Topologies model) handle cross-cutting
requirement ownership? Is the platform team the natural owner of capability K-Briefs?

**Why it matters:** A tool without a governance model for cross-team artifacts will
be ignored or duplicated. The ownership model is as important as the schema.

**How to answer:** Research Team Topologies patterns for cross-cutting concerns;
review how platform teams handle ADRs (Architectural Decision Records) at org scale.

---

### GAP-4: How does event-driven choreography change the verification model?

**What we believe:** In synchronous API architectures, the SoS contract is an OpenAPI
spec — a point-in-time, inspectable artifact. In event-driven architectures (Kafka,
SNS/SQS, NATS), the "contract" is an event schema plus temporal obligations
("audit-service must receive payment.executed within 5 seconds"). Verification is
not a static contract check — it is a temporal property over event sequences.

**What we need to know:** What tooling exists for temporal property verification across
event-driven services? AsyncAPI covers schema; does anything cover timing obligations
and ordering constraints? Is this related to TLA+, temporal logic, or runtime
verification approaches?

**Why it matters:** Most modern enterprise systems are event-driven. A SoS verification
approach that only handles synchronous APIs covers the wrong architecture.

**How to answer:** Research AsyncAPI tooling ecosystem, event-driven contract testing
(Pact has message support), and temporal logic verification tools for distributed systems.

---

### GAP-5: How must MTARP evolve for SoS context?

**What we believe:** MTARP needs a `system_requirement_ref` field carrying the
capability K-Brief ID and cross-repo trace context. But the session envelope (KB-2026-026)
was designed for single-repo continuity. Multi-repo sessions raise new questions:
can an agent working on payment-service read auth-service's code? Should it?

**What we need to know:** What is the right scoping model for a multi-repo autonomous
agent session? Should one agent instance span repos, or should separate agents per
repo be coordinated by a SoS orchestrator? What does the handoff envelope need to carry?

**Why it matters:** This is the protocol design decision that constrains the
implementation of aider-relay at SoS scale.

**How to answer:** Design spike — sketch two models (single spanning agent vs
per-repo agents + SoS orchestrator) and evaluate against the relay_loop.py architecture.

---

### GAP-6: Does academic literature exist at SoS + agentic coding intersection?

**What we believe:** KB-2026-034 surveyed the agentic coding literature and found no
V-model-explicit work. We did not specifically search for SoS + agentic or
multi-repo + LLM agent papers.

**What we need to know:** Is there academic work on LLM agents operating across
multiple repos or at system-of-systems level? ICSE, FSE, ASE, ISSTA proceedings
2023–2025 are the target venues.

**Why it matters:** If work exists, it may have solved GAP-1 or GAP-4 and we should
build on it. If nothing exists, the SoS + agentic framing is novel territory.

**How to answer:** Targeted literature search: "multi-repository LLM agent",
"system-of-systems software agents", "cross-service requirement traceability LLM".

---

### GAP-7: How does cross-repo vacuity manifest in practice and how is it currently detected?

**What we believe:** Cross-repo vacuity (a system-level requirement that is never
exercised across the full service chain) is the most common and most expensive
undetected failure mode in large distributed systems. It currently surfaces as
production incidents, not in test runs.

**What we need to know:** Are there documented cases of cross-service vacuity failures
and how they were discovered? Is distributed tracing (OTEL, Jaeger, Datadog APM) being
used retroactively to detect vacuous requirements in production?

**Why it matters:** If we can characterise the failure mode concretely (case studies,
incident reports), it strengthens the evaluation design (KB-2026-035 Layer 2) and the
paper thesis. It also grounds the tooling in a recognisable pain point.

**How to answer:** Review public incident post-mortems (Google SRE book, Slack/PagerDuty
incident databases, GitHub blog engineering posts) for cross-service requirement
failures.

---

## What This Unlocks (if gaps are closed)

| Gap closed | What becomes possible |
|---|---|
| GAP-1 | Know whether to build or integrate for cross-repo requirement tracing |
| GAP-2 | Connect contract testing to the V-model right side without building from scratch |
| GAP-3 | Design governance model that orgs will actually adopt |
| GAP-4 | Handle event-driven architectures — covers modern enterprise systems |
| GAP-5 | Protocol extension design for MTARP multi-repo sessions |
| GAP-6 | Position the research contribution accurately; avoid reinventing existing work |
| GAP-7 | Ground the SoS vacuity claim in documented production failures — makes the paper |

---

## Suggested Next K-Briefs (spawn from gaps)

| K-Brief | Gap | Type |
|---|---|---|
| KB-2026-037 | GAP-1 + GAP-6: Multi-repo agentic tooling and academic landscape | research |
| KB-2026-038 | GAP-2: Requirement-linked contract testing — what exists | research |
| KB-2026-039 | GAP-3: Cross-team capability ownership — Team Topologies patterns | research |
| KB-2026-040 | GAP-4: Event-driven SoS verification — temporal properties and tooling | research |
| KB-2026-041 | GAP-5: MTARP multi-repo protocol extension — design spike | design |
| KB-2026-042 | GAP-7: Cross-service vacuity in production — incident case studies | research |

---

## Related

- KB-2026-035: V-model agentic system architecture and design
- KB-2026-034: V-model in agentic coding — research landscape
- KB-2026-033: KBPD + Karpathy wiki + Graphify synthesis
- KB-2026-026: MTARP as A2A extension
