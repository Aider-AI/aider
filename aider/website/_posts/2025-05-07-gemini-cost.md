---
title: Gemini 2.5 Pro Preview 03-25 benchmark cost
excerpt: The $6.32 benchmark cost reported for Gemini 2.5 Pro Preview 03-25 was incorrect.
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Gemini 2.5 Pro Preview 03-25 benchmark cost

## Summary
The $6.32 cost reported to run the aider polyglot benchmark on
Gemini 2.5 Pro Preview 03-25 was incorrect.
The true cost was higher, possibly significantly so.
The incorrect cost has been removed from the leaderboard.

An investigation determined the primary cause was that the litellm
package (used by aider for LLM API connections) was not properly including reasoning tokens in 
the token counts it reported.
While an incorrect price-per-token entry for the model also existed in litellm's cost
database at that time, this was found not to be a contributing factor.
Aider's own internal, correct pricing data was utilized during the benchmark.

## Resolution

Litellm began correctly including reasoning tokens in the reported counts
on April 21, 2025 in 
commit [a7db0df](https://github.com/BerriAI/litellm/commit/a7db0df0434bfbac2b68ebe1c343b77955becb4b).
This change was released in litellm v1.67.1.
Aider picked up this change April 28, 2025 when it upgraded its litellm dependency 
from v1.65.7 to v1.67.4.post1
in commit [9351f37](https://github.com/Aider-AI/aider/commit/9351f37).
That dependency change shipped on May 5, 2025 in aider v0.82.3.

Unfortunately the 03-25 version of Gemini 2.5 Pro Preview is no longer available,
so it is not possible to re-run the benchmark to obtain an accurate cost.
As a possibly relevant comparison, the newer 05-06 version of Gemini 2.5 Pro Preview
completed the benchmark at a cost of about $37.

## Investigation detail

The version of litellm available at that time of the benchmark appears to have been
excluding reasoning tokens from the token counts it reported.
So even though aider had correct per-token pricing, it did not have the correct token counts
used during the benchmark.
This resulted in an underestimate of the benchmark costs.

The incorrect litellm database entry does not appear to have affected the aider benchmark costs.
Aider maintains and uses its own database of costs for some models, and it contained
the correct pricing at the time of the benchmark.
Aider appears to have
loaded the correct cost data from its database and made use of it during the benchmark.

Every aider benchmark report contains the git commit hash of the aider repository state used to
run the benchmark.
The 
[benchmark run in question](https://github.com/Aider-AI/aider/blob/edbfec0ce4e1fe86735c915cb425b0d8636edc32/aider/website/_data/polyglot_leaderboard.yml#L814)
was built from 
commit [0282574](https://github.com/Aider-AI/aider/commit/0282574).

Additional runs of the benchmark from that build verified that the error in litellm's
model cost database appears not to have been a factor:

- Aider's internal model database correctly overrides the litellm database, which contained an incorrect token cost at the time.
- The correct pricing is loaded from aider's internal model database and produces similar (incorrect) costs as the original run.
- Updating aider's internal model database with an absurdly high token cost resulted in an appropriately high benchmark cost report, demonstrating that the internal database costs were in effect.

This specific build of aider was then updated with various versions of litellm using `git biset`
to identify the first litellm commit where reasoning tokens counts were correctly reported.



## Timeline

Below is the full timeline of git commits related to this issue in the aider and litellm repositories.
Each entry has a UTC timestamp, followed by the original literal timestamp obtained from the
relevant source.

- 2025-04-04 19:54:45 UTC (Sat Apr 5 08:54:45 2025 +1300)
  - Correct value `"output_cost_per_token": 0.000010` for  `gemini/gemini-2.5-pro-preview-03-25` added to `aider/resources/model-metadata.json`
  - Commit [eda796d](https://github.com/Aider-AI/aider/commit/eda796d) in aider.

- 2025-04-05 16:20:01 UTC (Sun Apr 6 00:20:01 2025 +0800)
  - First litellm commit of `gemini/gemini-2.5-pro-preview-03-25` metadata, with incorrect price `"output_cost_per_token": 0.0000010`
  - Commit [cd0a1e6](https://github.com/BerriAI/litellm/commit/cd0a1e6) in litellm.

- 2025-04-10 01:48:43 UTC (Wed Apr 9 18:48:43 2025 -0700)
  - litellm commit updates `gemini/gemini-2.5-pro-preview-03-25` metadata, but not price
  - Commit [ac4f32f](https://github.com/BerriAI/litellm/commit/ac4f32f) in litellm.

- 2025-04-12 04:55:50 UTC (2025-04-12-04-55-50 UTC)
  - Benchmark performed.
  - Aider repo hash [0282574 recorded in benchmark results](https://github.com/Aider-AI/aider/blob/7fbeafa1cfd4ad83f7499417837cdfa6b16fe7a1/aider/website/_data/polyglot_leaderboard.yml#L814), without a "dirty" annotation, indicating that the benchmark was run on a clean checkout of the aider repo at commit [0282574](https://github.com/Aider-AI/aider/commit/0282574).
  - Correct value `"output_cost_per_token": 0.000010` is in `aider/resources/model-metadata.json` at this commit [0282574](https://github.com/Aider-AI/aider/blob/0282574/aider/resources/model-metadata.json#L357).

- 2025-04-12 15:06:39 UTC (Apr 12 08:06:39 2025 -0700)
  - Benchmark results added to aider repo.
  - Commit [7fbeafa](https://github.com/Aider-AI/aider/commit/7fbeafa) in aider.

- 2025-04-12 15:20:04 UTC (Sat Apr 12 19:20:04 2025 +0400)
  - litellm commit fixes `gemini/gemini-2.5-pro-preview-03-25` price metadata to `"output_cost_per_token": 0.00001`
  - Commit [93037ea](https://github.com/BerriAI/litellm/commit/93037ea) in litellm.

- 2025-04-22 05:48:00 UTC (Mon Apr 21 22:48:00 2025 -0700)
  - Litellm started including reasoning tokens in token count reporting.
  - Commit [a7db0df](https://github.com/BerriAI/litellm/commit/a7db0df0434bfbac2b68ebe1c343b77955becb4b) in litellm.
  - This fix was released in litellm v1.67.1.

- 2025-04-28 14:53:20 UTC (Mon Apr 28 07:53:20 2025 -0700)
  - Aider upgraded its litellm dependency from v1.65.7 to v1.67.4.post1, which included the reasoning token count fix.
  - Commit [9351f37](https://github.com/Aider-AI/aider/commit/9351f37) in aider.
  - This dependency change shipped on May 5, 2025 in aider v0.82.3.
