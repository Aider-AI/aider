---
title: R1+Sonnet set SOTA on aider's polyglot benchmark
excerpt: R1+Sonnet has set a new SOTA on the aider polyglot benchmark. At 14X less cost compared to o1.
highlight_image: /assets/r1-sonnet-sota.jpg
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# R1+Sonnet set SOTA on aider's polyglot benchmark
{: .no_toc }

<canvas id="editChart" width="800" height="450" style="margin-top: 20px"></canvas>

Aider supports [using a pair of models for coding](https://aider.chat/2024/09/26/architect.html):

- An Architect model is asked to describe how to solve the coding problem. Thinking/reasoning models often work well in this role.
- An Editor model is given the Architect's solution and asked to produce specific code editing instructions to apply those changes to existing source files.

**R1 as architect with Sonnet as editor has set a new SOTA of 64.0%** on the 
[aider polyglot benchmark](/2024/12/21/polyglot.html).
They achieve this at **14X less cost** compared to the previous o1 SOTA result.

o1 paired with Sonnet didn't produce better results than just using o1 alone.
Using various other models as editor didn't seem to improve o1 or R1 versus their solo scores.
This is in contrast to the first wave of thinking models like o1-preview and o1-mini,
which improved when paired with many different editor models.

o1 was set with reasoning effort high for these tests.

## Try it

Once you [install aider](https://aider.chat/docs/install.html),
you can use aider, R1 and Sonnet like this:

```bash
export DEEPSEEK_API_KEY=<your-key>
export ANTHROPIC_API_KEY=<your-key>

aider --architect --model r1 --editor-model sonnet
```

Or if you have an [OpenRouter](https://openrouter.ai) account:

```bash
export OPENROUTER_API_KEY=<your-key>

aider --architect --model openrouter/deepseek/deepseek-r1 --editor-model openrouter/anthropic/claude-3.5-sonnet
```

## Thinking output

There has been 
[some recent discussion](https://github.com/Aider-AI/aider/pull/2973)
about extracting the `<think>` tokens from R1's responses
and feeding them to Sonnet.
That was an interesting experiment, for sure.

To be clear, the results above are *not* using R1's thinking tokens, just the normal
final output. 
R1 is configured in aider's standard architect role with Sonnet as editor.
The benchmark results that used the thinking tokens appear to be worse than
the architect/editor results shared here.

## Results

<table style="width: 100%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: center;">Percent completed correctly</th>
      <th style="padding: 8px; text-align: center;">Percent using correct edit format</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: center;">Edit format</th>
      <th style="padding: 8px; text-align: center;">Total Cost</th>
    </tr>
  </thead>
  <tbody>
    {% assign edit_sorted = site.data.r1_architect | sort: 'pass_rate_2' | reverse %}
    {% for row in edit_sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px; text-align: center;">{{ row.pass_rate_2 }}%</td>
        <td style="padding: 8px; text-align: center;">{{ row.percent_cases_well_formed }}%</td>
        <td style="padding: 8px;"><code>{{ row.command }}</code></td>
        <td style="padding: 8px; text-align: center;">{{ row.edit_format }}</td>
        <td style="padding: 8px; text-align: center;">{% if row.total_cost == 0 %}?{% else %}${{ row.total_cost | times: 1.0 | round: 2 }}{% endif %}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<script src="https://unpkg.com/patternomaly/dist/patternomaly.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
{% assign data_source = edit_sorted %}
{% assign pass_rate_field = "pass_rate_2" %}
{% assign highlight_model = "+" %}
{% assign show_legend = false %}
{% include leaderboard.js %}
</script>
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
