---
id: KB-YYYY-NNN
type: limit
status: draft
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
related: []
---

# [Title: What Limit/Boundary Was Discovered]

## Context

Why understanding this limit matters for the project.

## Question

What boundary or limit were we trying to discover?

## Experiment

How we tested to find the limit:
- Test methodology
- Variables tested
- Measurement approach

## Findings

### The Limit

Where the system breaks or stops working:
- Quantitative boundary (e.g., "fails above 1000 connections")
- Qualitative boundary (e.g., "doesn't work on external repositories")

### Behavior Before Limit

How the system behaves within acceptable range.

### Behavior At/Beyond Limit

What happens when the limit is reached or exceeded:
- Failure modes
- Degradation patterns
- Error conditions

## Evidence

Data supporting the limit discovery:
- Test results
- Logs
- Metrics
- Artifacts

## Implications

What this limit means for:
- Architecture decisions
- Capacity planning
- Feature scope
- User expectations

## Recommendations

### Within Limit
How to operate safely within the boundary.

### Approaching Limit
Warning signs and mitigation strategies.

### Beyond Limit
What to do if the limit must be exceeded:
- Architectural changes required
- Alternative approaches
- Cost/complexity trade-offs

## Applicability

Where this limit applies:
- ✅ Applies to: [systems, scenarios, contexts]
- ❌ Does not apply to: [exceptions, special cases]

## Related Knowledge

- Related K-Briefs
- ADRs
- Documentation
- Issues
