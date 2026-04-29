# Knowledge Briefs (K-Briefs)

This directory contains structured knowledge artifacts generated during product development.

## What is a K-Brief?

A K-Brief is a **reusable record of learning** that captures:
- What we learned
- Why it matters
- Where it applies
- What evidence supports it

K-Briefs are **first-class artifacts**, not optional documentation.

## When to Create a K-Brief

Create a K-Brief when:
- ✅ A decision is made
- ✅ An experiment is run
- ✅ A failure occurs
- ✅ A performance boundary is discovered
- ✅ A trade-off is analyzed
- ✅ A design space is explored

## K-Brief Types

### 1. Trade-Off K-Brief
Captures relationships between competing variables.

**Template:** `templates/tradeoff.md`

**Example:** CLI proxy vs subprocess vs browser automation

### 2. Limit/Boundary K-Brief
Defines where something breaks or stops working.

**Template:** `templates/limit.md`

**Example:** Claude Pro usage window reset timing and error signals

### 3. Standard/Best Practice K-Brief
Captures proven solutions and patterns.

**Template:** `templates/standard.md`

**Example:** How to carry aider chat context across a model switch

### 4. Design Space K-Brief
Maps the range of possible solutions.

**Template:** `templates/design-space.md`

**Example:** Local proxy options for Claude Pro and ChatGPT Plus CLIs

### 5. Failure Mode K-Brief
Documents how systems fail and how to prevent it.

**Template:** `templates/failure-mode.md`

**Example:** Mid-task model switch causing context loss or format mismatch

## K-Brief Lifecycle

```
Knowledge Gap → Experiment → Findings → K-Brief → Reusable Knowledge
```

1. **Identify Gap** - What don't we know?
2. **Design Experiment** - How will we learn?
3. **Run Experiment** - Execute and observe
4. **Capture Findings** - Document what happened
5. **Create K-Brief** - Structure the knowledge
6. **Apply Knowledge** - Use in future decisions

## K-Brief Structure

All K-Briefs follow this structure:

```yaml
---
id: KB-YYYY-NNN
type: [tradeoff|limit|standard|design-space|failure-mode]
status: [draft|validated|deprecated]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag1, tag2, tag3]
related: [KB-YYYY-NNN, KB-YYYY-NNN]
---

# Title

## Context
Why this knowledge matters

## Question/Problem
What we needed to learn

## Experiment/Investigation
How we learned it

## Findings
What we discovered

## Evidence
Data, tests, artifacts supporting findings

## Implications
What this means for the project

## Recommendations
How to apply this knowledge

## Applicability
Where this knowledge applies (and doesn't)
```

## Querying K-Briefs

K-Briefs are stored as structured markdown with YAML frontmatter, making them:
- Human-readable
- Machine-queryable
- Version-controlled
- Linkable

**Search by type:**
```bash
grep -l "type: tradeoff" .kbriefs/*.md
```

**Search by tag:**
```bash
grep -l "tags:.*cli-provider" .kbriefs/*.md
```

**Find related:**
```bash
grep -l "related:.*KB-2026-001" .kbriefs/*.md
```

## K-Brief vs Other Artifacts

| Artifact | Purpose | Scope | Lifespan |
|----------|---------|-------|----------|
| K-Brief | Capture reusable knowledge | Specific learning | Long-term |
| ADR | Record architectural decision | Single decision | Permanent |
| Issue | Track work item | Task execution | Short-term |
| Documentation | Explain how things work | System behavior | Evolving |

K-Briefs are **knowledge assets** that compound over time.

## Philosophy

> "The highest-performing teams don't just build products faster — they learn faster and encode that learning into the system."
> — Allen C. Ward, Knowledge-Based Product Development

K-Briefs are how we encode learning into the system.
