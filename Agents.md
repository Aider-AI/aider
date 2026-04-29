# AGENTS.md

This file defines the **operating rules for AI coding agents** working in this repository.

Agents must read and follow this file before making changes.

The goal of this repository is to extend aider so it can leverage **consumer AI subscriptions** (Claude Pro, ChatGPT Plus) through their respective CLIs, enabling long-running tasks to continue across provider usage windows by switching models transparently.

---

## 0. Development Philosophy: Knowledge-Based Product Development

This repository follows **Knowledge-Based Product Development (KBPD)** principles.

Product development is a **knowledge-generation system**, not a task-execution system.

### Core Principles

#### Product Development = Learning System

Traditional approach:

```
Execute plan → hit milestones → ship
```

KBPD approach:

```
Identify knowledge gaps → run learning cycles → capture knowledge → make evidence-based decisions
```

#### Knowledge Gaps Are First-Class Artifacts

Before implementing, explicitly identify:

- What is unknown but critical to success
- What assumptions need validation
- What limits need discovery
- What trade-offs need quantification

#### Set-Based Concurrent Engineering

Explore multiple viable solutions in parallel, gradually narrowing based on evidence.

Do not prematurely converge on a single approach.

#### Evidence Before Commitment

Delay irreversible decisions until sufficient knowledge is available.

Use abstraction layers, interfaces, and feature flags to keep options open.

#### Knowledge Briefs (K-Briefs)

Capture learning in **structured, reusable artifacts** called K-Briefs.

K-Briefs are **first-class artifacts**, not optional documentation.

See `.kbriefs/Readme.md` for complete K-Brief system documentation.

### When to Create K-Briefs

Agents must create K-Briefs when:

- ✅ A decision is made
- ✅ An experiment is run
- ✅ A failure occurs
- ✅ A performance boundary is discovered
- ✅ A trade-off is analyzed
- ✅ A design space is explored

### K-Brief Types

1. **Trade-Off K-Brief** - Relationships between competing variables
2. **Limit/Boundary K-Brief** - Where something breaks or stops working
3. **Standard/Best Practice K-Brief** - Proven solutions and patterns
4. **Design Space K-Brief** - Range of possible solutions
5. **Failure Mode K-Brief** - How systems fail and prevention

Templates available in `.kbriefs/templates/`

### Agent K-Brief Workflow

#### Before Making Decisions

```bash
# Search for relevant K-Briefs
grep -r "tags:.*\[relevant-tag\]" .kbriefs/
```

#### During Experiments

Document findings for K-Brief creation:

- What was tested
- What was observed
- What was learned
- What evidence was collected

#### After Learning

Create K-Brief to capture knowledge:

```bash
# Use template
cp .kbriefs/templates/[type].md .kbriefs/KB-YYYY-NNN-[title].md
# Fill in structured content
# Commit as part of work
```

#### When Stuck

Check if a K-Brief exists for similar situations.

### Knowledge Compounds

Each K-Brief makes future work faster by:

- Preventing re-learning
- Accelerating decisions
- Reducing risk
- Building institutional memory

---

## 1. Project Purpose

`aider-relay` is a hard fork of [aider](https://github.com/paul-gauthier/aider) that adds:

- **CLI provider backends** — route model calls through the Claude CLI and ChatGPT CLI instead of (or in addition to) direct API keys
- **Subscription-aware model switching** — automatically switch to a fallback model when a provider's usage window is exhausted, carrying full context forward
- **Transparent continuity** — the developer's task continues uninterrupted across the model switch

The project inherits aider's full codebase and extends it minimally.

---

## 2. Architectural Principles

### Follow Gall's Law

Start with the **simplest working system** and evolve.

Do not design a complex system from scratch.

Complex systems must grow from simple working ones.

### Prefer Extension Over Modification

When adding capabilities:

1. Prefer **new modules** that hook into existing aider extension points
2. Prefer **subclassing** over modifying base classes
3. Only modify core aider files when no extension point exists

The existing aider codebase is the baseline. Minimize divergence from upstream so that future upstream changes can be rebased.

### Evidence Before Architecture

Before building provider integrations, validate:

- What CLI tools are available and how they expose APIs
- What error signals indicate usage exhaustion vs transient rate limits
- What the minimal proxy/adapter surface needs to be

Do not build the full provider abstraction until these are known.

### Keep Options Open

The CLI integration approach (proxy vs subprocess vs other) is **not yet decided**.

Use interfaces and feature flags so the approach can change without rewriting consumers.

---

## 3. Key Extension Points in Aider

Understanding these is essential before making changes:

### Model Switching (`SwitchCoder`)

`aider/commands.py:30` — `SwitchCoder` is an exception that triggers a model switch.

The outer loop in `aider/main.py:1159` catches it and creates a new `Coder` via `Coder.create(from_coder=coder, ...)`, carrying full chat history, open files, and cost totals.

This is the **primary mechanism** for fallback switching.

### Retry Loop (`base_coder.py:1449`)

The inner retry loop catches `LiteLLMExceptions`. Currently:
- `RateLimitError` → retry with exponential backoff
- `ContextWindowExceededError` → stop and report

We need to distinguish **transient rate limits** (retry) from **usage window exhaustion** (switch model).

### Model Configuration (`aider/models.py`)

`MODEL_ALIASES` maps short names to model strings. Custom provider models will be registered here.

`ModelSettings` dataclass controls per-model behaviour (edit format, caching, streaming, etc.).

### LiteLLM (`aider/llm.py`)

All API calls go through `litellm`. Custom providers can be integrated via litellm's `custom_llm_provider` or `api_base` override, keeping aider's call path intact.

---

## 4. What Agents Must Avoid

Agents must NOT:

- Modify aider core files unless no extension point exists
- Prematurely pick a CLI integration architecture before gaps are closed
- Implement provider backends without first validating the error signal taxonomy
- Add large abstractions before the simplest working path is proven
- Break existing aider functionality — all existing tests must remain green

---

## 5. Current Knowledge Gaps (KBPD Starting State)

These gaps must be closed before committing to implementation:

### Gap 1 — CLI Tool Availability
What CLIs exist for Claude Pro and ChatGPT Plus? Do they expose a local HTTP API?

### Gap 2 — Usage Exhaustion Signal
How does each provider signal "usage window exhausted" vs "transient rate limit"? What is the exact error code/message/HTTP status?

### Gap 3 — Proxy Architecture Options
What local proxy options exist (e.g. `claude-to-api`, custom FastAPI shim, subprocess pipe)? What are their reliability, latency, and maintenance trade-offs?

### Gap 4 — Context Fidelity Across Switch
What must be preserved when switching from Claude to GPT mid-task? Are there format differences that break the `from_coder` handoff?

### Gap 5 — Auto-Resume After Window Reset
Should the relay switch back to the original provider after the usage window resets? How do we know when the window has reset?

See `.kbriefs/` for K-Briefs as gaps are closed.

---

## 6. Development Loop

```
task lint
task test
```

Agents must not declare tasks complete if these fail.

---

## 7. Repository Layout

```
aider-relay/
│
├─ Agents.md          ← this file
├─ .kbriefs/          ← K-Brief knowledge system
│  ├─ Readme.md
│  └─ templates/
│
├─ aider/             ← forked aider source (extend, don't rewrite)
│  ├─ providers/      ← NEW: CLI provider adapters
│  └─ ...
│
└─ tests/
```

---

## 8. Contribution Expectations

Changes should:

- Close a named knowledge gap
- Be accompanied by a K-Brief when a decision or experiment is involved
- Keep existing aider tests green
- Prefer the smallest change that validates the hypothesis

---

End of Agents.md
