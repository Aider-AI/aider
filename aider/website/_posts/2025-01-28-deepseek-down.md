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

## Providers
{: .no_toc }

* TOC
{:toc}

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

```bash
# Set your API key using environment variables
export FIREWORKS_API_KEY=<your-key>
aider --model fireworks_ai/accounts/fireworks/models/deepseek-chat

# Or use the --api-key command line option
aider --model fireworks_ai/accounts/fireworks/models/deepseek-chat --api-key fireworks=<your-key>

# Or add it to .aider.conf.yml in your home directory or project root:
api-key:
  - fireworks=<your-key>
```

Create a `.aider.model.settings.yml` file in your home directory or git project root with settings like this:

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


## Hyperbolic

You can use [Hyperbolic's API](https://hyperbolic.xyz) as an OpenAI-compatible provider:

```bash
# Set your API key using environment variables
export OPENAI_API_BASE=https://api.hyperbolic.xyz/v1/
export OPENAI_API_KEY=<your-key>
aider --model openai/deepseek-ai/DeepSeek-V3

# Or use the --api-key command line option
aider --model openai/deepseek-ai/DeepSeek-V3 --api-key openai=<your-key>

# Or add it to .aider.conf.yml in your home directory or project root:
api-key:
  - openai=<your-key>
```

Create a `.aider.model.settings.yml` file in your home directory or git project root with settings like this:

```yaml
- name: openai/deepseek-ai/DeepSeek-V3
  edit_format: diff
  weak_model_name: null
  use_repo_map: true
  send_undo_reply: false
  lazy: false
  reminder: sys
  examples_as_sys_msg: true
  cache_control: false
  caches_by_default: true
  use_system_prompt: true
  use_temperature: true
  streaming: true
  editor_model_name: null
  editor_edit_format: null
  extra_params:
    max_tokens: 65536
```

## Ollama

You can run [DeepSeek V3 via Ollama](https://ollama.com/library/deepseek-v3).

```bash
# Pull the model
ollama pull deepseek-v3

# Start your ollama server
ollama serve

# In another terminal window...
export OLLAMA_API_BASE=http://127.0.0.1:11434 # Mac/Linux
setx   OLLAMA_API_BASE http://127.0.0.1:11434 # Windows, restart shell after setx

aider --model ollama/deepseek-v3
```

It's important to provide model settings, especially the `num_ctx` parameter to
set the context window.
Ollama uses a 2k context window by default, which is very small for working with aider.
Larger context windows will allow you to work with larger amounts of code,
but will use memory and increase latency.

Unlike most other LLM servers, Ollama does not throw an error if you submit a request that exceeds the context window. Instead, it just silently truncates the request by discarding the “oldest” messages in the chat to make it fit within the context window.

So if your context window is too small, you won’t get an explicit error. The biggest symptom will be that aider says it can’t see (some of) the files you added to the chat. That’s because ollama is silently discarding them because they exceed the context window.

Create a `.aider.model.settings.yml` file in your home directory or git project root with settings like this:

```yaml
- name: ollama/deepseek-v3
  edit_format: diff
  weak_model_name: null
  use_repo_map: true
  send_undo_reply: false
  lazy: false
  reminder: sys
  examples_as_sys_msg: true
  cache_control: false
  caches_by_default: true
  use_system_prompt: true
  use_temperature: true
  streaming: true
  extra_params:
    num_ctx: 8192 # How large a context window?
```

## Other providers

You will need to properly configure aider to work with DeepSeek V3 when served
via other providers:

- Determine the `--model` name to use.
- Provide your API key to aider.
- Add model settings to `.aider.model.settings.yml`.


Adapt the `.aider.model.settings.yml` shown above for Fireworks. You will need to change the `name` field to match you chosen provider's model naming scheme.

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
