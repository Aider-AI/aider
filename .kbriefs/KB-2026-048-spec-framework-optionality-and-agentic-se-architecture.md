---
id: KB-2026-048
type: design-space
status: draft
created: 2026-05-08
updated: 2026-05-08
tags: [spec-driven, architecture, optionality, speckit, openspec, bmad, v-model, kbpd, brownfield]
related: [KB-2026-031, KB-2026-033, KB-2026-034, KB-2026-035, KB-2026-036, KB-2026-047]
---

# Spec Framework Optionality and Agentic SE Architecture

## Context

aider-relay already has three relevant strands of work:

1. MTARP as a session continuation protocol for provider handoff.
2. KBPD K-Briefs as the decision and evidence layer.
3. An early SpecKit-compatible bootstrap integration.

The open question is not whether spec-driven development is useful. The open question is
which spec-driven paradigm should be treated as primary, and how to avoid locking the
architecture to a single framework while the space is still moving quickly.

Three external frameworks are immediately relevant:

- Spec Kit
- OpenSpec
- BMad Method

At the same time, existing KB work in this repo already points toward a V-model-style
verification overlay and a KBPD + graph + task-spec stack rather than a single planning
tool becoming the whole architecture.

## Problem Statement

How should aider-relay support spec-driven and workflow-driven development frameworks
without coupling MTARP, relay orchestration, or the future verification layer to one
tool's file layout, command set, or process philosophy?

## Design Space Dimensions

| Dimension | Description | Range |
|---|---|---|
| Canonical artifact model | What counts as the source of truth | Tool-native files -> internal canonical schema |
| Brownfield fitness | How well the approach fits existing codebases | Weak -> strong |
| Workflow depth | How much process and role structure is imposed | Lightweight -> highly orchestrated |
| Agent portability | How easily the same planning artifacts move across coding agents | Narrow -> broad |
| Customization model | How easily teams can extend or override behavior | Fixed -> layered extension |
| Verification strength | How naturally the approach connects to test, trace, and audit | Planning-only -> verification-aware |
| Multi-repo/team readiness | How well the approach scales beyond one repo and one session | Solo repo -> team/system level |

## Options in the Space

### Option A: SpecKit-first integration

Treat Spec Kit as the primary planning and implementation framework inside aider-relay.

- How it works:
  - Use Spec Kit artifact flow as the default project structure.
  - Lean on `/speckit.constitution`, `/speckit.specify`, `/speckit.plan`,
    `/speckit.tasks`, and `/speckit.implement`.
  - Reuse Spec Kit extensions, presets, workflows, and agent integrations instead of
    inventing equivalents.
- Strengths:
  - Richest customization surface among the three options studied.
  - Explicit extension, preset, and workflow mechanisms already exist.
  - Strong greenfield feature flow from constitution to implementation.
- Weaknesses:
  - More opinionated than OpenSpec.
  - Tighter coupling to a particular command and artifact lifecycle.
  - "One active integration per project" is workable, but it reinforces tool-specific
    setup at the project boundary.
- Evidence:
  - Spec Kit CLI covers project init, integrations, extensions, presets, and workflows.
  - Multiple presets can be stacked, and multiple extensions can coexist.

### Option B: OpenSpec-first planning layer

Treat OpenSpec as the primary checked-in planning layer and keep aider-relay focused on
execution, handoff, and verification.

- How it works:
  - Use `openspec/specs/*` as long-lived capability specs.
  - Use `openspec/changes/*` as the unit of planned change.
  - Feed change proposals, design, tasks, and spec deltas into relay execution.
- Strengths:
  - Strongest statement of agent portability.
  - Brownfield-friendly and lightweight.
  - "Spec delta" concept maps cleanly to code review and intent review.
  - Keeps specs in the repo instead of in agent-specific state.
- Weaknesses:
  - Less governance and extension surface than Spec Kit today.
  - Team/multi-repo features are explicitly still in development.
  - Less mature as a process ecosystem than BMad.
- Evidence:
  - OpenSpec positions itself as universal across coding agents.
  - It generates proposal, design, tasks, and spec delta artifacts.
  - It explicitly targets mature codebases and checked-in specs.

### Option C: BMad-first workflow orchestration

Treat BMad Method as the primary process and agent orchestration framework, with
aider-relay acting as one execution substrate under it.

- How it works:
  - Use BMad phases for analysis, planning, solutioning, and implementation.
  - Use agent skills, workflows, and modules to run structured work.
  - Optionally use TEA for stronger testing and traceability.
- Strengths:
  - Strongest workflow and agent-role structure.
  - Strong customization and module system.
  - Best current fit for team process, skill generation, and specialized roles.
  - TEA is directly relevant to traceability and test architecture.
- Weaknesses:
  - Most process-heavy option.
  - More of a workflow operating system than a neutral artifact format.
  - Outputs can become tool- and workflow-specific unless normalized.
  - Node-based installer and generated skills add operational surface area.
- Evidence:
  - BMad has explicit phases, named agents, workflows, generated skills, modules, and
    a builder for custom agents/workflows/modules.
  - TEA goes beyond built-in QA toward test architecture and traceability.

### Option D: Internal canonical model with pluggable adapters

Create a methodology-neutral internal schema and adapter layer. Treat Spec Kit,
OpenSpec, BMad, and native KBPD/TASK files as import/export surfaces rather than the
core model.

- How it works:
  - Define an internal representation for intent, plan, change, execution context,
    verification obligations, and trace links.
  - Write adapters for Spec Kit, OpenSpec, BMad, and native project artifacts.
  - Keep MTARP tied to the internal model, not to any framework's native file layout.
- Strengths:
  - Preserves optionality while the ecosystem is unstable.
  - Keeps protocol and execution layers neutral.
  - Supports mixing strengths: OpenSpec for brownfield planning, Spec Kit for
    extensions/presets, BMad for orchestration, V-model overlay for verification.
  - Best long-term fit with KBPD and the repo's existing V-model thinking.
- Weaknesses:
  - Highest architecture design burden now.
  - Requires semantic mapping between frameworks that do not line up perfectly.
  - Risk of building an abstraction too early if kept too broad.
- Evidence:
  - Existing KBs already separate knowledge, execution, and verification concerns.
  - MTARP's value increases when handoff is independent of any one agent or workflow tool.

### Option E: Native aider-relay-only spec stack

Ignore external frameworks and grow the current `.specify`, `specs/`, `TASK.md`, and
K-Brief conventions into a custom in-repo methodology.

- How it works:
  - Expand current local conventions.
  - Add more commands directly to aider-relay.
  - Keep all process semantics home-grown.
- Strengths:
  - Maximum control.
  - No dependency on external framework churn.
- Weaknesses:
  - Rebuilds ecosystem capability already available elsewhere.
  - Hardest path for community interoperability.
  - Most likely to overfit local preferences too early.

## Design Space Map

| Option | Canonicality | Brownfield fit | Workflow depth | Portability | Customization | Verification fit | Recommended role |
|---|---|---|---|---|---|---|---|
| A: SpecKit-first | Medium | Medium | Medium | Medium | High | Medium | Strong adapter target |
| B: OpenSpec-first | Medium | High | Low | High | Medium | Medium | Strong planning adapter |
| C: BMad-first | Low | High | High | Medium | High | High | Strong orchestration adapter |
| D: Canonical core + adapters | High | High | Configurable | High | High | High | Recommended architecture |
| E: Native-only | High | Medium | Medium | Low | Medium | Medium | Not recommended as default |

## Dominated Solutions

- Hard-code one external framework into MTARP payload semantics.
  - Dominated because protocol neutrality is more valuable than short-term convenience.
- Treat workflow engine and canonical artifact format as the same thing.
  - Dominated because it collapses planning, execution, and verification into one layer.

## Pareto Frontier

- Option D is the best architectural direction.
- Option B is the best lightweight planning influence.
- Option A is the best extension/preset ecosystem influence.
- Option C is the best workflow/orchestration and traceability influence.

The practical frontier is not "pick one." It is:

1. Internal canonical model
2. Thin adapters for external frameworks
3. Verification overlay independent of the planning framework

## Traditional SE Theory: What Still Helps

Several older bodies of software engineering theory remain highly relevant:

- Requirements engineering
  - Still the right discipline for separating intent from implementation.
- Architecture and ADR-style decision capture
  - Still necessary because code generation does not remove trade-offs.
- V-model traceability
  - More relevant, not less, when agents can produce code that passes tests while
    missing the underlying requirement.
- Brownfield reverse engineering
  - Still central because most enterprise reality is existing code, not greenfield.
- Incremental and agile planning
  - Still correct as a guard against over-planning and heavyweight ceremony.
- Configuration management and version control
  - More important because specs, plans, prompts, generated code, and verification
    artifacts all need lineage.

## Traditional SE Theory: What Must Move

The agentic era changes several assumptions:

- Specs are no longer passive documentation.
  - They are operational context consumed directly by agents.
- Session continuity is now an architectural concern.
  - Human continuity used to bridge broken context. MTARP exists because agents do not
    share human memory.
- Traceability must become machine-readable.
  - Human-readable docs are not enough when multiple agents, providers, and workflows
    transform artifacts automatically.
- Verification must target requirement satisfaction, not only test pass rate.
  - Existing KB-2026-034 and KB-2026-035 already identify vacuity as a central problem.
- Brownfield reconstruction becomes first-class.
  - Agents often need to recover intent from code before they can safely modify it.
- Workflow state joins code and docs as a governed artifact.
  - Plans, tasks, checkpoints, and handoff envelopes are part of the system, not
    disposable coordination chatter.

## Architecture Implications

### 1. Keep MTARP methodology-neutral

MTARP should not encode Spec Kit paths, OpenSpec folder names, or BMad trigger names as
protocol semantics. Instead it should reference normalized concepts such as:

- `spec_framework`
- `artifact_refs`
- `change_id`
- `acceptance_refs`
- `verification_refs`
- `trace_refs`

### 2. Add a planning kernel layer

The architecture should gain an internal "planning kernel" between raw framework files
and relay execution. Suggested internal concepts:

- `CapabilitySpec`
- `ChangeProposal`
- `ImplementationPlan`
- `TaskGraph`
- `ExecutionContextPack`
- `VerificationObligation`
- `TraceLink`

### 3. Use adapters, not forks, for external frameworks

Suggested adapters:

- `SpecKitAdapter`
  - Parse constitution, feature specs, plan, tasks, and optionally extension metadata.
- `OpenSpecAdapter`
  - Parse long-lived capability specs and per-change deltas.
- `BMadAdapter`
  - Parse PRD, architecture, epics/stories, project-context, and optional TEA outputs.
- `NativeKBPDAdapter`
  - Convert K-Briefs, TASK specs, and local planning documents into the canonical model.

### 4. Treat V-model as an overlay, not a competitor

The V-model work in KB-2026-034 and KB-2026-035 should sit above the planning kernel as
the verification and traceability layer. In other words:

- Spec Kit / OpenSpec / BMad answer "how do we structure planning?"
- V-model overlay answers "how do we prove the change satisfies intent?"
- MTARP answers "how does the work continue across sessions/providers?"

### 5. Separate greenfield and brownfield flows

The frameworks differ most here:

- Spec Kit is strongest for constitution-led feature flow.
- OpenSpec is strongest for lightweight checked-in brownfield planning.
- BMad is strongest for established-project documentation and guided workflow.

The architecture should expose different entry points rather than pretending one flow
fits all repos.

## Evidence & Data

### Spec Kit

- Core lifecycle commands: constitution, specify, plan, tasks, implement
- Integrations, extensions, presets, workflows
- One active integration per project
- Multiple extensions can coexist
- Multiple presets can be stacked

Sources:

- https://github.com/github/spec-kit
- https://raw.githubusercontent.com/github/spec-kit/main/README.md
- https://raw.githubusercontent.com/github/spec-kit/main/docs/reference/overview.md
- https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md

### OpenSpec

- Universal planning layer across many coding agents
- Specs live in repo by capability
- Changes produce proposal, design, tasks, and spec deltas
- Strong brownfield-first positioning
- Team/multi-repo/workspaces explicitly still in development

Sources:

- https://openspec.dev/

### BMad Method

- Agile-inspired phased workflow
- Specialized agents, workflows, generated skills
- Customization and module system
- Brownfield document-project workflow
- TEA module adds test architecture and traceability

Sources:

- https://docs.bmad-method.org/
- https://docs.bmad-method.org/reference/workflow-map/
- https://docs.bmad-method.org/reference/agents/
- https://docs.bmad-method.org/reference/modules/
- https://docs.bmad-method.org/reference/commands/
- https://docs.bmad-method.org/how-to/customize-bmad/

## Knowledge Gaps to Close

### Gap 1: Canonical intermediate representation

What is the smallest internal schema that can represent all three frameworks without
collapsing important distinctions?

### Gap 2: Brownfield backfill confidence

How should the system record confidence when specs are reconstructed from code rather
than authored first?

### Gap 3: Cross-framework traceability semantics

How should requirement IDs, story IDs, task IDs, and verification obligations map when
artifacts come from different frameworks?

### Gap 4: Verification attachment points

Which verification artifacts belong in the planning kernel, which belong in MTARP, and
which belong only in the V-model overlay?

### Gap 5: Command UX

Should users invoke framework-native commands (`/speckit.plan`, `/openspec:proposal`,
`bmad-create-prd`) or methodology-neutral aider-relay commands that delegate under the
hood?

## Convergence Strategy

| Phase | Action | Why |
|---|---|---|
| Phase 1 | Freeze protocol neutrality for MTARP | Avoid tool-specific lock-in |
| Phase 2 | Define internal planning kernel schema | Preserve optionality |
| Phase 3 | Implement SpecKit adapter first | Already partially present in repo |
| Phase 4 | Implement OpenSpec adapter second | Strong comparison point for brownfield planning |
| Phase 5 | Prototype BMad adapter and TEA bridge | Learn what to borrow for orchestration and verification |
| Phase 6 | Add V-model verification overlay | Turn planning into auditable execution |
| Phase 7 | Decide default workflows by project type | Greenfield, brownfield, enterprise, solo |

## Applicability

- Applies to:
  - aider-relay architecture decisions about planning, execution, and verification layers
  - MTARP schema evolution
  - Future command design for spec-driven workflows
  - Brownfield and greenfield onboarding paths

- Does not apply to:
  - Choosing one framework permanently right now
  - Replacing MTARP with an external planning framework
  - Treating workflow tooling as proof of requirement satisfaction

