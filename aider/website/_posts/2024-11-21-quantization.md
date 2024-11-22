---
title: Quantization matters
excerpt: Open source LLMs are becoming very powerful, but pay attention to how you (or your provider) is quantizing the model. It can strongly affect code editing skill.
highlight_image: /assets/quantization.jpg
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Quantization matters

Open source models like Qwen 2.5 32B Instruct are performing very well on
aider's code editing benchmark, rivaling closed source frontier models.
But pay attention to how your model is being quantized, as it
can strongly impact code editing skill.
Heavily quantized models are often used by cloud API providers
and local model servers like Ollama.

<canvas id="quantChart" width="800" height="450" style="margin: 20px 0"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
{% include quant-chart.js %}
</script>

The graph above compares 3 different versions of the Qwen 2.5 Coder 32B Instruct model,
served both locally and from cloud providers.

- The [HuggingFace weights](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct) served via [glhf.chat](https://glhf.chat).
- The results from [OpenRouter's mix of providers](https://openrouter.ai/qwen/qwen-2.5-coder-32b-instruct/providers) which serve the model with different levels of quantization.
- Ollama locally serving [qwen2.5-coder:32b-instruct-q4_K_M)](https://ollama.com/library/qwen2.5-coder:32b-instruct-q4_K_M), which has `Q4_K_M` quantization.

The best version of the model rivals GPT-4o, while the worst performer
is more like GPT-3.5 Turbo level.

## Choosing providers with OpenRouter

OpenRouter allows you to ignore specific providers in your
[preferences](https://openrouter.ai/settings/preferences).
This can be effective to exclude highly quantized or otherwise
undesirable providers.

{: .note }
The original version of this article included incorrect Ollama models
that were not Qwen 2.5 Coder 32B Instruct.
