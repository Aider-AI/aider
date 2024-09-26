---
title: A draft post.
excerpt: With a draft summary.
highlight_image: /assets/linting.jpg
draft: true
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Separating code reasoning and editing

Here's a table containing the benchmark data for different model configurations:

| Model | Junior Model | Junior Edit Format | Pass Rate 2 (%) | Seconds per Case | Total Cost ($) |
|-------|--------------|---------------------|-----------------|-------------------|----------------|
| claude-3.5-sonnet | claude-3.5-sonnet | junior-diff | 80.5 | 25.1 | 4.95 |
| o1-mini | gpt-4o | junior-diff | 70.7 | 23.7 | 9.32 |
| gpt-4o | gpt-4o | junior-diff | 75.2 | 18.2 | 6.09 |
| o1-preview | gpt-4o | junior-diff | 80.5 | 42.3 | 39.38 |
| o1-preview | claude-3.5-sonnet | junior-diff | 82.7 | 44.9 | 37.62 |
| o1-mini | deepseek | junior-diff | 69.2 | 52.2 | 5.79 |
| o1-preview | deepseek | junior-diff | 80.5 | 73.2 | 35.79 |
| o1-preview | deepseek | junior-whole | 85.0 | 67.4 | 35.32 |

This table provides a comparison of different model configurations, showing their performance in terms of pass rate, processing time, and cost.


