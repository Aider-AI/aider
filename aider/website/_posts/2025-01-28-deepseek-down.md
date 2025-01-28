---
title: DeepSeek API issues - Alternative providers
excerpt: DeepSeek's API has been experiencing reliability issues. Here are alternative providers you can use.
highlight_image: /assets/deepseek-down.jpg
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# DeepSeek API issues - Alternative providers
{: .no_toc }

<canvas id="editChart" width="800" height="450" style="margin-top: 20px"></canvas>

DeepSeek's API has been experiencing significant reliability issues for the past 24-48+ hours, with many users reporting downtime and overload problems.

If you're affected by these issues, several alternative providers offer access to DeepSeek models. This article compares their performance on aider's polyglot benchmark to help you choose a reliable alternative.

## Using alternative providers

The benchmark results below show that several providers offer comparable or better performance than DeepSeek's native API. To switch providers, you'll need to:

1. Sign up for an account with your chosen alternative provider
2. Get their API key
3. Update your aider configuration to use their endpoint

For example, to use OpenRouter:

```bash
export OPENROUTER_API_KEY=<your-key>
aider --model openrouter/deepseek/deepseek-v3
```

## Configuring model settings

You may want to configure specific settings when using alternative providers. For example, you can control which OpenRouter providers are used to serve the model, or set other model parameters.

Create a `.aider.model.settings.yml` file in your home directory or git project root with settings like this:

```yaml
- name: openrouter/deepseek/deepseek-v3
  extra_params:
    extra_body:
      provider:
        # Only use these providers, in this order
        order: ["Novita"]
        # Don't fall back to other providers
        allow_fallbacks: false
```

See [OpenRouter's provider routing docs](https://openrouter.ai/docs/provider-routing) for full details on these settings.

See [Advanced model settings](https://aider.chat/docs/config/adv-model-settings.html#model-settings) for more details about aider's model settings files.

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
    {% assign edit_sorted = site.data.deepseek-down | sort: 'pass_rate_2' | reverse %}
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
