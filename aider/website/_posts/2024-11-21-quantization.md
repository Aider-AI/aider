---
title: Quantization matters
excerpt: Open source LLMs are becoming very powerful, but pay attention to how you (or your) provider is quantizing the model. It strongly affects code editing skill.
highlight_image: /assets/quantization.jpg
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Quantization matters

Open source models like Qwen 2.5 32B are performing very well on
aider's code editing benchmark, rivaling closed source frontier models.
But pay attention to how your model is being quantized, as it
can strongly impact code editing skill.
Heavily quantized models are often used by cloud API providers
and local model servers like ollama.

The graph below compares 4 different versions of the Qwen 2.5 32B model,
served both locally and from cloud providers:

<canvas id="quantChart" width="800" height="450" style="margin: 20px 0"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
{% include quant-chart.js %}
</script>
