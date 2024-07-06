---
parent: Connecting to LLMs
nav_order: 850
---

# Editing format

Aider uses different "edit formats" to collect code edits from different LLMs.
The "whole" format is the easiest for an LLM to use, but it uses a lot of tokens
and may limit how large a file can be edited.
Models which can use one of the diff formats are much more efficient,
using far fewer tokens.
Models that use a diff-like format are able to 
edit larger files with less cost and without hitting token limits.

Aider is configured to use the best edit format for the popular OpenAI and Anthropic models
and the [other models recommended on the LLM page](https://aider.chat/docs/llms.html).
For lesser known models aider will default to using the "whole" editing format
since it is the easiest format for an LLM to use.

If you would like to experiment with the more advanced formats, you can
use these switches: `--edit-format diff` or `--edit-format udiff`.
