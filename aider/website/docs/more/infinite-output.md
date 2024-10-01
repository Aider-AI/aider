---
parent: More info
nav_order: 920
description: Aider can handle "infinite output" from models that support prefill.
---

# Infinite output

LLM providers limit how much output a model can generate from a single request.
This is usually called the output token limit.

Aider is able to work around this limit with models that support
"prefilling" the assistant response.
When you use aider with a model that supports prefill, you will see
"infinite output" noted in the announcement lines displayed at launch:

```
Aider v0.58.0
Main model: claude-3-5-sonnet-20240620 with diff edit format, prompt cache, infinite output
```

Models that support prefill can be primed to think they started their response
with a specific piece of text.
You can put words in their mouth, and they will continue generating
text from that point forward.

When aider is collecting code edits from a model and
it hits the output token limit,
aider simply initiates another LLM request with the partial
response prefilled.
This prompts the model to continue where it left off,
generating more of the desired response.
This prefilling of the partially completed response can be repeated,
allowing for very long outputs.
Joining the text across these output limit boundaries 
requires some heuristics, but is typically fairly reliable.

Aider supports "infinite output" for models that support "prefill",
such as:

<!--[[[cog
# TODO: list the models
cog.out(text)
]]]-->

<!--[[[end]]]-->


