---
id: KB-2026-019
type: design-space
status: draft
created: 2026-04-29
updated: 2026-04-29
tags: [context-relay, handoff, tier-portability, completion-api, local-llm, validation]
related: [KB-2026-007, KB-2026-017, KB-2026-016, KB-2026-010]
---

# Cross-Tier Session Portability

## Context & Problem Statement

KB-2026-007 defines the handoff matrix for context relay when switching providers. KB-2026-017 establishes that Tier A (agentic CLI) providers require session lock-in. The **unvalidated assumption** is that Tier B (completion API) and Tier C (hybrid) providers can meaningfully continue work started by a Tier A agentic session — given only git context and injected file contents.

This is a practical gap: the Phase 3 routing architecture routes cheap tasks to local LLM (Tier B) and falls back to CLI (Tier A) when complexity increases. But if the Tier A → Tier B handoff produces incoherent sessions, or the Tier B → Tier A re-escalation loses state, the cascade scheme is non-functional.

## The Core Portability Question

Can a **Tier B completion API** (e.g., Ollama running Llama-3-8B) meaningfully continue work started by a **Tier A agentic CLI** (e.g., Claude Code) if provided:
- The original task description
- A git diff of changes made so far
- The contents of files in scope
- A subtask checklist of what is done and what remains

**This has not been validated.** The assumption comes from KB-2026-007 Option 1 (git-only handoff), which is validated only for Tier A → Tier A switches.

## Portability Dimensions

### 1. Context window capacity

Tier B models (local LLMs at 7B–13B parameters) typically have 4K–8K token context windows. A git diff + file contents for a non-trivial codebase can easily exceed this. The handoff prompt may need to be truncated or summarised before injection.

Tier A providers (Claude Code, Codex) have 200K+ context in their respective sessions and can load files lazily on demand via tool calls. Tier B completion APIs receive everything upfront — injecting too little gives an incomplete picture; injecting too much overflows context.

### 2. Code editing capability

Tier A providers produce diffs or edit files directly. Tier B completion APIs return text — the relay must parse the returned text for code blocks and apply edits as a post-processing step.

For Tier B to continue Tier A work, the relay must implement:
- Code extraction from markdown fenced blocks
- Patch application (unified diff format or whole-file replacement)
- Git commit on behalf of the model

None of this infrastructure exists in aider-relay today.

### 3. Coherence of continuation

Even with context injected, a local LLM may:
- Repeat work already done (not recognising git diff as evidence of completion)
- Miss implicit constraints established in the Tier A session ("we decided to use PyJWT")
- Produce syntactically correct but functionally wrong code if context is lossy

This is the Routesplain finding applied to session continuity: task-domain coherence degrades when the model doesn't have the same context depth as the original session.

### 4. Re-escalation path

If local Tier B cannot handle the task continuation, it must signal back to the relay that escalation is needed. Tier B models don't emit `exhausted` events — they just produce poor output. A confidence signal (logprob entropy if llama.cpp is the backend) or a structured output validation step is needed to detect this.

## Design Space

### Option A: Tier B continuation not supported (Phase 1-3)
Only allow Tier A ↔ Tier A switches (Claude Code ↔ Codex). Tier B providers handle new tasks only, never handoffs. Simple, avoids all portability complexity, but loses the cost-efficiency benefit of the cascade model.

### Option B: Tier B continuation with full file injection (Phase 4)
On Tier A → Tier B switch:
1. Identify files-in-scope from `RelayContext` (KB-2026-007 Phase 2)
2. Inject full file contents into Tier B context
3. Relay parses Tier B output for code blocks and applies patches
4. On Tier B → Tier A escalation, relay builds new handoff prompt with updated git diff

- Completeness: Medium — depends on files-in-scope being accurate
- Complexity: High — relay must implement code extraction and patch application
- Risk: Context overflow for large files-in-scope sets

### Option C: Tier B continuation with chunked handoff (Phase 5)
Inject files one at a time with multi-turn dialogue: "Here is the task and file A. What changes would you make?" Then: "Apply your suggestion to file A. Now here is file B..." The relay orchestrates the dialogue.

- Completeness: High — files are injected progressively to fit context window
- Complexity: Very high — relay must manage multi-turn file injection dialogue
- Latency: High — many round trips

## Convergence Strategy

**Phase 3:** Option A — Tier B handles new sessions only, never continuations. Document this as a known limitation.

**Phase 4:** Validate Option B with a controlled test: take a Tier A session that made one file edit, switch to Tier B (Ollama Llama-3-8B), inject git diff + file contents, ask it to continue. Measure whether the output is coherent and whether the relay can apply the resulting patch.

**Phase 5:** Option C if Option B's context window constraint proves blocking.

## Validation Test (Phase 4 target)

```
1. Start relay_loop with Claude Code on task: "Add a hello() function to utils.py, then add a goodbye() function"
2. After Claude Code adds hello(), trigger sim_exhaust to switch to Ollama Tier B
3. Inject: task description + git diff showing hello() added + utils.py current contents
4. Observe: Does Ollama correctly add goodbye() without re-adding hello()?
5. Measure: context tokens used, output coherence, patch applicability
```

## Open Questions

1. What is the minimum viable Tier B model size for SE task continuation? 7B parameters is the smallest practically runnable local model — is it sufficient for simple continuation tasks?
2. Can the relay detect Tier B failure to continue coherently without a judge call? Or does it require a logprob confidence signal?
3. Does Codex (Tier A) have the same handoff problem when resuming from a session it didn't start? The `sim-exhaust-after` test is designed to answer this for Tier A → Tier A.

## Applicability

- ✅ Blocks Phase 4 cascade routing design
- ✅ Must be validated before adding any Tier B provider to the active provider pool
- ✅ Informs whether `RelayContext.to_handoff_prompt()` needs tier-specific logic beyond what KB-2026-007 specifies
- ❌ Do not assume Tier B continuation works — it is unvalidated at the time of writing
