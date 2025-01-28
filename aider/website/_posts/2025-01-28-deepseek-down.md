---
title: Alternative DeepSeek V3 providers
excerpt: DeepSeek's API has been experiencing reliability issues. Here are alternative providers you can use.
#highlight_image: /assets/deepseek-down.jpg
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Alternative DeepSeek V3 providers
{: .no_toc }

<canvas id="editChart" width="800" height="450" style="margin-top: 20px"></canvas>

DeepSeek's API has been experiencing significant reliability issues for the past 24-48+ hours, with many users reporting downtime and overload problems.
Their [status page](https://status.deepseek.com) notes an ongoing incident.

If you're affected by these issues, several alternative providers offer access to DeepSeek V3. This article compares their performance on aider's polyglot benchmark to help you choose a reliable alternative.

## OpenRouter

[OpenRouter offers many DeepSeek providers](https://openrouter.ai/deepseek/deepseek-chat/providers)
through their unified API.
You can use aider with OpenRouter like this:

```bash
# Set your API key using environment variables
export OPENROUTER_API_KEY=<your-key>
aider --model openrouter/deepseek/deepseek-chat

# Or use the --api-key command line option
aider --model openrouter/deepseek/deepseek-chat --api-key openrouter=<your-key>

# Or add it to .aider.conf.yml in your home directory or project root:
api-key:
  - openrouter=<your-key>
```

OpenRouter automatically monitors their providers and routes requests to stable
APIs and away from those experiencing unreliable performance.

But not all providers serve the same version of open source models, and not
all have the same privacy guarantees.
You can control which OpenRouter providers are used to serve the model via
[aider's model settings](https://aider.chat/docs/config/adv-model-settings.html#model-settings).
Create a `.aider.model.settings.yml` file in your home directory or git project root with settings like this:

```yaml
- name: openrouter/deepseek/deepseek-chat
  extra_params:
    extra_body:
      provider:
        # Only use these providers, in this order
        order: ["Novita"]
        # Don't fall back to other providers
        allow_fallbacks: false
```

See [OpenRouter's provider routing docs](https://openrouter.ai/docs/provider-routing) for more details.


## Fireworks

# add the code block showing how to set FIREWORKS_API_KEY
# also show --model fireworks_ai/accounts/fireworks/models/deepseek-chat
# ai!

```yaml
- name: fireworks_ai/accounts/fireworks/models/deepseek-chat
  edit_format: diff
  weak_model_name: null
  use_repo_map: true
  send_undo_reply: false
  lazy: false
  reminder: sys
  examples_as_sys_msg: true
  extra_params:
    max_tokens: 8192
  cache_control: false
  caches_by_default: true
  use_system_prompt: true
  use_temperature: true
  streaming: true
```


## Other providers

You will need to properly configure aider to work with DeepSeek V3 when served
via alternate providers.
Aider is pre-configured to work well with V3 served via DeepSeek's direct API and via OpenRouter.

For other providers, you should adapt this example configuration for using DeepSeek V3
via Fireworks.
You'll need to change the `name` field to match you chosen provider's model naming scheme.

See [Advanced model settings](https://aider.chat/docs/config/adv-model-settings.html#model-settings) for details about all aider model settings

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
{% assign highlight_model = "DeepSeek" %}
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
