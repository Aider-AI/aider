---
id: KB-2026-004
type: tradeoff
status: draft
created: 2026-04-27
updated: 2026-04-27
tags: [model-switching, context, chat-history, from-coder, claude, openai]
related: [KB-2026-002, KB-2026-003, KB-2026-005]
---

# Context Fidelity Across Model Switch

## Context

aider's `SwitchCoder` / `from_coder` mechanism already transfers chat history, open files, cost totals, and edit format across model switches. But switching between Claude and GPT mid-task introduces potential fidelity issues: different edit formats, different system prompt expectations, different handling of multi-turn history.

## Variables

### Variable 1: Edit Format Compatibility
- **Definition**: Whether the incoming model can correctly interpret outgoing edit format markers
- **Risk**: Claude uses `diff` or `whole` formats; switching to GPT may require format re-negotiation
- **Existing mitigation**: `Coder.create()` with `summarize_from_coder=True` summarizes history when edit format changes

### Variable 2: Message History Size
- **Definition**: Total token count of `done_messages` carried forward
- **Risk**: A large Claude conversation may exceed GPT-4o's context window when switched
- **Existing mitigation**: aider's summarizer (`ChatSummary`) compresses history

### Variable 3: System Prompt Compatibility
- **Definition**: Whether the new model's system prompt is coherent with accumulated history
- **Risk**: Claude-specific formatting instructions in the system prompt may confuse GPT
- **Existing mitigation**: `Coder.create()` rebuilds the system prompt from scratch for the new model

### Variable 4: Reasoning Content
- **Definition**: `<thinking>` blocks or reasoning tags in Claude responses
- **Risk**: If these are in `done_messages` when handed to GPT, it will see confusing tokens
- **Existing mitigation**: `remove_reasoning_content()` in `base_coder.py:1522`

## Known Aider Handoff Mechanism

```python
# base_coder.py ~160-184 (from_coder path)
update = dict(
    fnames=list(from_coder.abs_fnames),
    done_messages=done_messages,        # compressed if format changes
    cur_messages=from_coder.cur_messages,
    aider_commit_hashes=from_coder.aider_commit_hashes,
    total_cost=from_coder.total_cost,
    ...
)
```

The `done_messages` are summarized when `edit_format` changes — this is the primary safety net.

## Open Questions

1. **Does summarization always succeed?** The code has a `try/except ValueError` fallback that keeps full history if summarization fails. On a long Claude session, full history handed to GPT may overflow.

2. **Does the summarizer use the old model or new model?** If the summarizer calls the old (exhausted) model to generate the summary, it will fail. Need to verify `ChatSummary` uses the weak model.

3. **Are there Claude-specific message roles or content types** (e.g. `cache_control` headers, tool use blocks) that would be invalid in a GPT message array?

4. **How does the current edit format affect GPT?** If aider was in `diff` mode with Claude and switches to GPT with `diff` mode, does GPT produce valid diffs?

## Experiment Required

1. Manually trigger a `SwitchCoder` from a Claude model to a GPT model mid-conversation
2. Inspect the `done_messages` array handed to the new coder
3. Check for any Claude-specific content that would confuse GPT
4. Verify the summarizer uses the weak model (not the main model)

## Implications

- **Low risk** if the switch always triggers summarization (forcing a clean history)
- **Medium risk** if format-compatible switches skip summarization and carry raw Claude messages to GPT
- **High risk** if Claude-specific message content (cache headers, tool blocks) reaches GPT

## Recommendations (provisional)

Force `summarize_from_coder=True` on any cross-provider switch, even if edit formats match, to ensure a clean handoff.

## Applicability

- ✅ All cross-provider model switches
- ❌ Same-provider switches (e.g. Claude Sonnet → Claude Haiku) — existing mechanism sufficient
