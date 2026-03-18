---
parent: Architecture Overview
nav_order: 150
---

# Infinite Output Trick

Models that support the `supports_assistant_prefill` capability can resume a reply after hitting the API's output token limit.  `base_coder.send_messages()` detects the `FinishReasonLength` exception and resends the partially generated text as a prefilled assistant message.  The model continues from that point, allowing Aider to gather arbitrarily long diffs.

```python
except FinishReasonLength:
    self.multi_response_content = self.get_multi_response_content_in_progress()
    messages[-1]['content'] = self.multi_response_content
    # resend request with assistant_prefill
```

The collected fragments are joined heuristically before being applied to the working tree.  This trick enables large refactors even with strict output limits.

