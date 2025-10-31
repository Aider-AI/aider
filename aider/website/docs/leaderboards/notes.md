---
parent: Aider LLM Leaderboards
nav_order: 800
---

# Benchmark notes

## Notes on pricing

All pricing information is the cost to run the benchmark at the time it was
run.
Providers change their pricing and sometimes introduce entirely novel pricing structures.
Pricing is provided on a *best efforts* basis, and may not always be current
or fully accurate.

## Notes on benchmarking results

The key benchmarking results are:

- **Percent completed correctly** - Measures what percentage of the coding tasks that the LLM completed successfully. To complete a task, the LLM must solve the programming assignment *and* edit the code to implement that solution.
- **Percent using correct edit format** - Measures the percent of coding tasks where the LLM complied with the edit format specified in the system prompt. If the LLM makes edit mistakes, aider will give it feedback and ask for a fixed copy of the edit. The best models can reliably conform to the edit format, without making errors.


## Notes on the edit format

Aider uses different "edit formats" to collect code edits from different LLMs.
The "whole" format is the easiest for an LLM to use, but it uses a lot of tokens
and may limit how large a file can be edited.
Models which can use one of the diff formats are much more efficient,
using far fewer tokens.
Models that use a diff-like format are able to 
edit larger files with less cost and without hitting token limits.

Aider is configured to use the best edit format for the popular OpenAI and Anthropic models
and the [other models recommended on the LLM page](/docs/llms.html).
For lesser known models aider will default to using the "whole" editing format
since it is the easiest format for an LLM to use.
