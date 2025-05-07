---
title: A note on Gemini 2.5 Pro Preview 0325 pricing
excerpt: The low price reported for Gemini 2.5 Pro Preview 0325 appears to be correct.
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# A note on Gemini 2.5 Pro Preview 0325 pricing

# Timeline

- 2025-04-04 19:54:45 UTC (Sat Apr 5 08:54:45 2025 +1300)
  - Commit eda796d feat: Add metadata and settings for gemini-2.5-pro-preview-03-25
  - Correct value `"output_cost_per_token": 0.000010` added to `aider/resources/model-metadata.json`

- 2025-04-05 16:20:01 UTC (Sun Apr 6 00:20:01 2025 +0800)
  - First litellm commit of `gemini/gemini-2.5-pro-preview-03-25` metadata, with incorrect price `"output_cost_per_token": 0.0000010`
  - Commit cd0a1e6

- 2025-04-10 01:48:43 UTC (Wed Apr 9 18:48:43 2025 -0700)
  - litellm commit updates `gemini/gemini-2.5-pro-preview-03-25` metadata, but not price
  - commit ac4f32f

- 2025-04-12 04:55:50 UTC (2025-04-12-04-55-50 UTC)
  - Benchmark performed 
  - Repo hash 0282574 recorded in benchmark results, without "dirty" indicating it was run on a clean checkout of the repo at commit 0282574.
  - Correct value `"output_cost_per_token": 0.000010` is in `aider/resources/model-metadata.json` at commmit 0282574
  - Confirmed that aider built and run from commit 0282574 honors `output_cost_per_token` from `aider/resources/model-metadata.json` by putting in an absurdly high value and benchmarking `gemini/gemini-2.5-pro-preview-03-25`

- 2025-04-12 15:06:39 UTC (Apr 12 08:06:39 2025 -0700)
  - Benchmark results added to repo

- 2025-04-12 15:20:04 UTC (Sat Apr 12 19:20:04 2025 +0400)
  - 2025-04-12 15:20:04 UTC (Sat Apr 12 15:20:04 2025 UTC)
  - litellm commit fixes `gemini/gemini-2.5-pro-preview-03-25` price metadata to `"output_cost_per_token": 0.00001`
  - commit 93037ea
