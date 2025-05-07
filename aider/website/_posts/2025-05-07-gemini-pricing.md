---
title: Gemini 2.5 Pro Preview 0325 benchmark pricing
excerpt: The low price reported for Gemini 2.5 Pro Preview 0325 appears to be correct.
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Gemini 2.5 Pro Preview 0325 benchmark pricing

There has been some concern about the low $6 price reported to run
Gemini 2.5 Pro Preview 0325
in the
aider leaderboard.
There are a couple of reasons for concern:

- Aider uses litellm, which had an incorrect price for output tokens in their database at the time of the benchmark.
- The recent benchmark of the 0506 version of Gemini 2.5 Pro Preview reports much higher costs.

This note reviews and audits the original 0325 benchmark results to investigate the reported price.

The incorrect litellm database entry does **not** appear to have affected the aider benchmark.
Aider maintains and uses its own database of costs for some models, and it contained
the correct pricing at the time of the benchmark and correctly loaded it.
Re-running the benchmark with the same aider built from commit hash [0282574](https://github.com/Aider-AI/aider/commit/0282574) 
loads the correct pricing from aider's local db
and produces similar costs as the original run.

It appears that litellm changed the way it reports token usage
between the benchmark of Gemini 2.5 Pro 0325 and today's 0506 benchmark.
At that commit 0282574, aider was using litellm v1.65.3.
Using the same aider built from 0282574, but with the latest litellm v1.68.1
produces benchmark results with higher costs.


# Timeline

- 2025-04-04 19:54:45 UTC (Sat Apr 5 08:54:45 2025 +1300)
  - Correct value `"output_cost_per_token": 0.000010` added to `aider/resources/model-metadata.json`
  - Commit [eda796d](https://github.com/Aider-AI/aider/commit/eda796d) in aider.

- 2025-04-05 16:20:01 UTC (Sun Apr 6 00:20:01 2025 +0800)
  - First litellm commit of `gemini/gemini-2.5-pro-preview-03-25` metadata, with incorrect price `"output_cost_per_token": 0.0000010`
  - Commit [cd0a1e6](https://github.com/BerriAI/litellm/commit/cd0a1e6) in litellm.

- 2025-04-10 01:48:43 UTC (Wed Apr 9 18:48:43 2025 -0700)
  - litellm commit updates `gemini/gemini-2.5-pro-preview-03-25` metadata, but not price
  - Commit [ac4f32f](https://github.com/BerriAI/litellm/commit/ac4f32f) in litellm.

- 2025-04-12 04:55:50 UTC (2025-04-12-04-55-50 UTC)
  - Benchmark performed 
  - Aider repo hash [0282574 recorded in benchmark results](https://github.com/Aider-AI/aider/blob/7fbeafa1cfd4ad83f7499417837cdfa6b16fe7a1/aider/website/_data/polyglot_leaderboard.yml#L814), without "dirty", indicating that the benchmark was run on a clean checkout of the aider repo at commit [0282574](https://github.com/Aider-AI/aider/commit/0282574).
  - Correct value `"output_cost_per_token": 0.000010` is in `aider/resources/model-metadata.json` at this commit [0282574](https://github.com/Aider-AI/aider/blob/0282574/aider/resources/model-metadata.json#L357)
  - Confirmed that aider built and run from commit [0282574](https://github.com/Aider-AI/aider/commit/0282574) honors `output_cost_per_token` from `aider/resources/model-metadata.json` by putting in an absurdly high value and benchmarking `gemini/gemini-2.5-pro-preview-03-25`

- 2025-04-12 15:06:39 UTC (Apr 12 08:06:39 2025 -0700)
  - Benchmark results added to repo
  - Commit [7fbeafa](https://github.com/Aider-AI/aider/commit/7fbeafa) in aider.

- 2025-04-12 15:20:04 UTC (Sat Apr 12 19:20:04 2025 +0400)
  - litellm commit fixes `gemini/gemini-2.5-pro-preview-03-25` price metadata to `"output_cost_per_token": 0.00001`
  - Commit [93037ea](https://github.com/BerriAI/litellm/commit/93037ea) in litellm.
