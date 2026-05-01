---
id: KB-2026-031
type: research
status: active
created: 2026-04-30
updated: 2026-04-30
tags: [task-specification, spec-driven-development, agents-md, agentic-coding, evidence]
related: [KB-2026-030, KB-2026-021]
---

# Agentic Task Specification: What Works and the Evidence

## Purpose

Inform the structure of TASK.md files used to drive autonomous multi-agent coding
sessions via aider-relay, based on published evidence rather than intuition.

---

## Spec-Driven Development

A spec is treated as the executable source of truth. Agents implement against the spec,
not against a vague verbal description. Implementation details are left to the agent;
the spec defines *what success looks like*, not *how to achieve it*.

Documented adoption: Kiro IDE reported 2-week-to-2-day cuts on feature builds. Augment
Code's Intent platform uses a Coordinator → Implementer → Verifier agent chain, all
driven by a shared spec. Martin Fowler documented the tooling landscape in 2025.

---

## What the Evidence Shows (by source strength)

### Very strong — Anthropic's own guidance (Claude Code Best Practices)

Direct guidance from the team that builds Claude Code:

1. **Provide verification criteria first.** Described as "the single highest-leverage
   thing you can do." Write test cases and acceptance criteria before the task
   description. The agent uses them to self-check without human feedback loops.

2. **Explore → Plan → Code sequence.** Use Plan Mode to let the agent research before
   implementing. Prevents solving the wrong problem.

3. **CLAUDE.md should be concise** (≤150 lines). Include: bash commands the agent
   can't guess, non-obvious code style rules, architectural decisions. Not exhaustive
   documentation — it's loaded at every session start.

4. **For autonomous tasks:** Run an "interview" session where the agent asks clarifying
   questions → produces a SPEC.md → then execute in a fresh session focused solely on
   implementation.

5. **Provide the agent a verification method** (test commands, expected output) so it
   can self-check without asking.

### Strong — AGENTS.md convention (2,500+ repository analysis, GitHub research)

Industry standard across Claude Code, Cursor, Windsurf, Copilot. Stewarded by the
Agentic AI Foundation.

**What works (by frequency in high-performing repos):**
- Executable commands with exact syntax (`task test`, not "run the tests")
- Tech stack with exact versions and file locations
- Code style shown as real examples, not described in prose
- Explicit three-tier constraint model (see below)
- Nearest-file precedence for monorepos (subdirectory AGENTS.md overrides root)

**Critical finding:** A bad AGENTS.md is worse than no docs at all. Vague or
contradictory instructions degrade agent performance more than silence.

**Optimal length:** <60 lines ideal; >150 lines agents begin ignoring content.

### Strong — SWE-Bench / SWE-agent benchmarks (academic, reproducible)

Task specs that include:
- Problem statement grounded in failing unit tests
- Interface specifications
- Concrete test suites

...resolve at 30–40% success rates. Underspecified tasks: <10%.

SWE-agent (NeurIPS 2024): performance strongly correlated with spec clarity and
language (Go/Python outperform JavaScript/TypeScript).

### Moderate (surprising) — AGENTbench context file study

Tested 138 tasks with: no context file / LLM-generated file / developer-written file.

**Finding:** LLM-generated context files *reduce* success by 2–3% and increase cost
by 20%+. Developer-written files improve success by only ~4% with 19% cost overhead.

**Implication:** The narrative that "better specs always help more" is overstated.
Verification criteria and workflow structure matter more than exhaustive context.

### Consistent (anecdotal) — practitioner community

Across Reddit, HN, Twitter/X:
- Multi-step numbered workflows: "one of the strongest patterns" — moves agents from
  unable-to-complete to correct-first-try
- Acceptance criteria + file lists + test-first specs cluster as success factors
- Real examples from the codebase beat abstract descriptions every time
- "Vibe coding" (vague goal, no criteria) fails reliably

---

## Documented Failure Modes

| Failure mode | Description |
|---|---|
| Too vague | "Implement a function" — no test cases, no expected behaviour |
| Too prescriptive | Dictating implementation approach; wastes context, kills creativity |
| Missing verification | No way for agent to self-check; every error requires human loop |
| Wrong scope | Task too large for one pass, or so fragmented context fills before completion |
| Ambiguous boundaries | Unclear what the agent must not touch |
| Static artifacts | Spec written once and never updated; agents work from stale context |
| Context overload | Dumping all docs without hierarchy; agents start ignoring rules |

Microsoft's taxonomy of agentic failures adds:
- **Tool storm / retrieval thrash** — exploration without direction
- **Information asymmetry** — agent must discover codebase incrementally
- **Siloed context** — agent lacks the full picture across fragmented data

---

## The Three-Tier Constraint Model

Consistently cited as a high-signal pattern across tools and researchers:

```
Always do:   [safe autonomous actions — agent proceeds without asking]
Ask first:   [high-impact or risky changes — agent pauses for confirmation]
Never do:    [absolute restrictions — agent must not cross these lines]
```

---

## Recommended TASK.md Structure (evidence-based)

```markdown
# Task: [Specific title]

## Objective
[1-2 sentences: what does success look like? Not how to achieve it.]

## Acceptance Criteria
[Testable, numbered — these come FIRST per Anthropic guidance]
1. `task test` passes with no failures
2. [Specific output / behaviour]
3. [Edge case handled]

## Scope
- Modify: [exact file list or directories]
- Do not touch: [migrations, secrets, unrelated modules]
- Reuse: [existing patterns / modules to build on]

## Workflow
[Numbered steps — strongest structural pattern]
1. [Step with success signal]
2. [Step with success signal]
...

## Constraints
- Always do: commit after each logical unit of work; run `task lint` before committing
- Ask first: changes to public API contracts, new dependencies, schema migrations
- Never do: modify .env files, force-push, delete existing tests

## Context
- Related patterns: [path/to/example]
- Architecture note: [one non-obvious thing the agent needs to know]
- Run `task ci` to verify the full pipeline passes
```

**Target length: 60–100 lines.** Under 60 is ideal. Over 150 the agent begins to
skip content. Verification criteria are the highest-leverage element — prioritise those
over detailed context if you have to choose.

---

## Key Sources

- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [How to write a great AGENTS.md (GitHub Blog, 2,500+ repo analysis)](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)
- [SWE-agent: Agent-Computer Interfaces (NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf)
- [AGENTbench context file impact study](https://agentic-academy.ai/posts/agents-md-context-files-evaluation/)
- [Microsoft: Taxonomy of Failure Modes in Agentic AI](https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/Taxonomy-of-Failure-Mode-in-Agentic-AI-Systems-Whitepaper.pdf)
- [Spec-Driven Development tooling (Martin Fowler)](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)
- [CodeScout: contextual problem statement enhancement (arXiv:2603.05744)](https://arxiv.org/html/2603.05744v2)
