---
title: Details matter with open source models
excerpt: Open source LLMs are becoming very powerful, but pay attention to how you (or your provider) are serving the model. It can affect code editing skill.
highlight_image: /assets/quantization.jpg
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Details matter with open source models
{: .no_toc }

<canvas id="quantChart" width="800" height="600" style="margin: 20px 0"></canvas>

Open source models like Qwen 2.5 32B Instruct are performing very well on
aider's code editing benchmark, rivaling closed source frontier models.

But pay attention to how your model is being served and quantized, 
as it can impact code editing skill.
Open source models are often available at a variety of quantizations,
and can be served with different token limits.
These details matter when working with code.

The graph above and table below compares different versions of the Qwen 2.5 Coder 32B Instruct model,
served both locally and from a variety of cloud providers.

- The [HuggingFace BF16 weights](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct) served via [glhf.chat](https://glhf.chat).
- [4bit and 8bit quants for mlx](https://t.co/cwX3DYX35D).
- The results from [OpenRouter's mix of providers](https://openrouter.ai/qwen/qwen-2.5-coder-32b-instruct/providers) which serve the model with different levels of quantization.
- Results from OpenRouter's providers, both served via OpenRouter and directly to their own APIs.
- Ollama locally serving different quantizations from the [Ollama model library](https://ollama.com/library/qwen2.5-coder:32b-instruct-q4_K_M) with 8k+
context windows.
- An Ollama fp16 quantization served with Ollama's default 2k context window.

### Pitfalls and details

This benchmarking effort highlighted a number of pitfalls and details specific to open source
models which
can have a significant impact on their ability to correctly edit code:

- **Quantization** -- Open source models are often available at dozens of different quantizations.
Most seem to only modestly decrease code editing skill, but stronger quantizations
do have a real impact.
- **Context window** -- Cloud providers can decide how large a context window to accept,
and they often choose differently. Ollama's local API server
defaults to a tiny 2k context window,
and silently discards data that exceeds it. Such a small window has
catastrophic effects on performance, without throwing obvious hard errors.
- **Output token limits** -- Open source models are often served with wildly
differing output token limits. This has a direct impact on how much code the
model can write or edit in a response.
- **Buggy cloud providers** -- While benchmarking Qwen 2.5 Coder 32B Instruct
and DeepSeek V2.5, I discovered
multiple cloud providers with broken or buggy API endpoints.
They seemed
to be returning results different from expected based on the advertised
quantization and context sizes.
The harm caused to the code editing benchmark varied from serious
to catastrophic.
One provider scored 0.5% on the benchmark with DeepSeek V2.5, a highly capable model.

Closed source, proprietary models don't typically have these issues.
They are owned and operated by the organization that created them,
and typically served with specific, predictable context window and output token limits.
Their quantization level is usually unknown, but fixed and unchanging for all users.

### Conclusions

The best versions of the Qwen model rival GPT-4o, while the worst performing
quantization is more like the older GPT-4 Turbo when served competently.
Even an otherwise excellent fp16 quantization falls to GPT-3.5 Turbo levels of performance
if run with Ollama's default 2k context window.

### Sections
{: .no_toc }

- TOC
{:toc}

## Benchmark results

{: .note :}
These are results from single benchmark runs, so expect normal variance of +/- 1-2%.

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
{% include quant-chart.js %}
</script>

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
Unlike most other LLM servers, Ollama does not throw an error if you submit
a request that exceeds the context window.
Instead, it just silently truncates the request by discarding the "oldest" messages
in the chat to make it fit within the context window.

Except for the single 2k context result,
all of the Ollama results above were collected with at least an 8k context window.
An 8k window is large enough to attempt all the coding problems in the benchmark.
Aider sets Ollama's context window to 8k by default, starting in aider v0.65.0.

You can change the Ollama server's context window with a 
[`.aider.model.settings.yml` file](https://aider.chat/docs/config/adv-model-settings.html#model-settings)
like this:

```
- name: ollama/qwen2.5-coder:32b-instruct-fp16
  extra_params:
    num_ctx: 8192
```

## Choosing providers with OpenRouter

OpenRouter allows you to ignore specific providers in your
[preferences](https://openrouter.ai/settings/preferences).
This can be used to limit your OpenRouter requests to be
served by only your preferred providers.

## Notes

This article went through many revisions as I received feedback from
numerous members of the community.
Here are some of the noteworthy learnings and changes:

- The first version of this article included incorrect Ollama models.
- Earlier Ollama results used the too small default 2k context window,
artificially harming the benchmark results.
- The benchmark results appear to have uncovered a problem in the way
OpenRouter was communicating with Hyperbolic.
They fixed the issue 11/24/24, shortly after it was pointed out.
