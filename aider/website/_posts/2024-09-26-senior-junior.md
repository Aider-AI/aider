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

<table>
  <thead>
    <tr>
      <th>Senior</th>
      <th>Junior</th>
      <th>Junior Edit Format</th>
      <th>Pass Rate (%)</th>
      <th>Average Time (sec)</th>
      <th>Total Cost ($)</th>
    </tr>
  </thead>
  <tbody>
    {% for group in grouped_data %}
      {% for item in group.items %}
        <tr>
          <td>{{ item.model }}</td>
          <td>{{ item.junior_model }}</td>
          <td>{{ item.junior_edit_format }}</td>
          <td>{{ item.pass_rate_2 }}</td>
          <td>{{ item.seconds_per_case }}</td>
          <td>{{ item.total_cost }}</td>
        </tr>
      {% endfor %}
      {% unless forloop.last %}
        <tr><td colspan="6"><hr></td></tr>
      {% endunless %}
    {% endfor %}
  </tbody>
</table>

This table provides a comparison of different model configurations, showing their performance in terms of pass rate, processing time, and cost. The data is grouped by the Senior model and sorted by the highest Pass Rate within each group (in descending order). Within groups, rows are sorted by decreasing Pass Rate.


