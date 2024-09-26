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

{% assign sorted_data = site.data.senior | sort: "pass_rate_2" | reverse %}
{% assign grouped_data = sorted_data | group_by: "model" %}

| Senior | Junior | Junior Edit Format | Pass Rate (%) | Average Time (sec) | Total Cost ($) |
|--------|--------|---------------------|----------------|---------------------|----------------|
{% for group in grouped_data %}
{% for item in group.items %}
| {{ item.model }} | {{ item.junior_model }} | {{ item.junior_edit_format }} | {{ item.pass_rate_2 }} | {{ item.seconds_per_case }} | {{ item.total_cost }} |
{% endfor %}
{% unless forloop.last %}
|--------|--------|---------------------|----------------|---------------------|----------------|
{% endunless %}
{% endfor %}
|--------|--------|---------------------|----------------|---------------------|----------------|

This table provides a comparison of different model configurations, showing their performance in terms of pass rate, processing time, and cost. The data is grouped by the Senior model and sorted by the highest Pass Rate within each group (in descending order). Within groups, rows are sorted by decreasing Pass Rate.


