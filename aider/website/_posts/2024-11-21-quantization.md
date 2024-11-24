---
title: Quantization matters
excerpt: Open source LLMs are becoming very powerful, but pay attention to how you (or your provider) is quantizing the model. It can affect code editing skill.
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
can impact code editing skill.
Heavily quantized models are often used by cloud API providers
and local model servers like Ollama or MLX.

<canvas id="quantChart" width="800" height="500" style="margin: 20px 0"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
{% include quant-chart.js %}
</script>

The graph above compares different versions of the Qwen 2.5 Coder 32B Instruct model,
served both locally and from cloud providers.

- The [HuggingFace BF16 weights](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct) served via [glhf.chat](https://glhf.chat).
- [4bit and 8bit quants for mlx](https://t.co/cwX3DYX35D).
- The results from [OpenRouter's mix of providers](https://openrouter.ai/qwen/qwen-2.5-coder-32b-instruct/providers) which serve the model with different levels of quantization.
- Ollama locally serving different quantizations from the [Ollama model library](https://ollama.com/library/qwen2.5-coder:32b-instruct-q4_K_M).
- Other API providers.

The best version of the model rivals GPT-4o, while the worst performer
is more like GPT-4 level.

{: .note }
This article is being updated as additional benchmark runs complete.


<input type="text" id="quantSearchInput" placeholder="Search..." style="width: 100%; max-width: 800px; margin: 10px auto; padding: 8px; display: block; border: 1px solid #ddd; border-radius: 4px;">

<table style="width: 100%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: center;">Percent completed correctly</th>
      <th style="padding: 8px; text-align: center;">Percent using correct edit format</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: center;">Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% assign quant_sorted = site.data.quant | sort: 'pass_rate_2' | reverse %}
    {% for row in quant_sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px; text-align: center;">{{ row.pass_rate_2 }}%</td>
        <td style="padding: 8px; text-align: center;">{{ row.percent_cases_well_formed }}%</td>
        <td style="padding: 8px;"><code>{{ row.command }}</code></td>
        <td style="padding: 8px; text-align: center;">{{ row.edit_format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<style>
  tr.selected {
    color: #0056b3;
  }
  table {
    table-layout: fixed;
  }
  td, th {
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
  td:nth-child(3), td:nth-child(4) {
    font-size: 12px;
  }
</style>

<script>
document.getElementById('quantSearchInput').addEventListener('keyup', function() {
    var input = this.value.toLowerCase();
    var rows = document.querySelectorAll('tbody tr');
    
    rows.forEach(function(row) {
        var text = row.textContent.toLowerCase();
        if(text.includes(input)) {
            row.style.display = '';
            row.classList.add('selected');
        } else {
            row.style.display = 'none';
            row.classList.remove('selected');
        }
    });
});
</script>

## Setting Ollama's context window size

[Ollama uses a 2k context window by default](https://github.com/ollama/ollama/blob/main/docs/faq.md#how-can-i-specify-the-context-window-size),
which is very small for working with aider.

All of the Ollama results above were collected with at least an 8k context window, which
is large enough to attempt all the coding problems in the benchmark.

You can set the Ollama server's context window with a 
[`.aider.model.settings.yml` file](https://aider.chat/docs/config/adv-model-settings.html#model-settings)
like this:

```
- name: aider/extra_params
  extra_params:
    num_ctx: 8192
```

That uses the special model name `aider/extra_params` to set it for *all* models. You should probably use a specific model name like:

```
- name: ollama/qwen2.5-coder:32b-instruct-fp16
  extra_params:
    num_ctx: 8192
```

## Choosing providers with OpenRouter

OpenRouter allows you to ignore specific providers in your
[preferences](https://openrouter.ai/settings/preferences).
This can be effective to exclude highly quantized or otherwise
undesirable providers.


{: .note }
Earlier versions of this article included incorrect Ollama models,
and also included some Ollama results with the too small default 2k
context window.
