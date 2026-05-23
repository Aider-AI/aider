---
parent: Connecting to LLMs
nav_order: 510
---

# OrcaRouter

Aider can connect to [models provided by OrcaRouter](https://www.orcarouter.ai/models),
an OpenAI-compatible LLM meta-router that exposes 150+ upstream models
(OpenAI, Anthropic, Google, DeepSeek, xAI, Qwen, MiniMax, Kimi, Z.ai, ...) under
a single API key.

You'll need an [OrcaRouter API key](https://www.orcarouter.ai).

First, install aider:

{% include install.md %}

Then configure your API key:

```
export ORCAROUTER_API_KEY=<key> # Mac/Linux
setx   ORCAROUTER_API_KEY <key> # Windows, restart shell after setx
```

Start working with aider and OrcaRouter on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Use any model from OrcaRouter's catalog
aider --model orcarouter/openai/gpt-4o
aider --model orcarouter/anthropic/claude-opus-4.7
aider --model orcarouter/deepseek/deepseek-v3.1

# List models known to aider with the orcarouter/ prefix
aider --list-models orcarouter/
```

## Adaptive routing with `orcarouter/auto`

OrcaRouter ships a virtual router named `auto` that automatically picks
an upstream for each request based on configurable strategies (`cheapest`,
`balanced`, `quality`, `adaptive`, `gated_adaptive`). You can target it with
the built-in alias:

```bash
aider --model orcarouter-auto
# equivalent to: aider --model orcarouter/orcarouter/auto
```

The routing policy and the upstream pool are configured in the
[OrcaRouter console](https://www.orcarouter.ai/console/routing).

{: .tip }
When using `orcarouter/orcarouter/auto` with aider's tool-calling features,
make sure the router pool only contains tool-capable upstream models, or pin
a specific model such as `orcarouter/openai/gpt-4o` to avoid 4xx errors from
upstreams that do not support function calling.

## Provider routing preferences

OrcaRouter accepts an `extra_body` block on chat completion requests for
routing preferences (e.g. fallback chains). You can configure it via a
`.aider.model.settings.yml` file:

```yaml
- name: orcarouter/openai/gpt-4o
  extra_params:
    extra_body:
      models: ["openai/gpt-4o-mini", "openai/gpt-4o"]
      route: "fallback"
```

See [Advanced model settings](https://aider.chat/docs/config/adv-model-settings.html#model-settings)
for more details about model settings files.
