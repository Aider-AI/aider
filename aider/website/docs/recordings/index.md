---
title: Screen recordings
has_children: true
nav_order: 75
has_toc: false
description: Screen recordings of aider building aider.
highlight_image: /assets/recordings.jpg
---

# Screen recordings

Below are a series of screen recordings of the aider developer using aider
to enhance aider.
They contain commentary that describes how aider is being used,
and might provide some inspiration for your own use of aider.

{% assign sorted_pages = site.pages | where: "parent", "Screen recordings" | sort: "nav_order" %}
{% for page in sorted_pages %}
- [{{ page.title }}]({{ page.url | relative_url }}) - {{ page.description }}
{% endfor %}

