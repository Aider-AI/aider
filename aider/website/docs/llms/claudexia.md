---
parent: Connecting to LLMs
nav_order: 410
---

# Claudexia

[Claudexia](https://claudexia.tech) is a pay-per-token gateway that exposes
Anthropic Claude and OpenAI GPT models through an OpenAI-compatible API.
It is convenient for users who want to pay per token (SBP / card / USDT) and
access Claude and GPT models without a US-based account.

To use Claudexia with aider, you'll need a
[Claudexia API key](https://claudexia.tech).

First, install aider:

{% include install.md %}

Then configure your API key and endpoint:

```
# Mac/Linux:
export OPENAI_API_BASE=https://api.claudexia.tech/v1
export OPENAI_API_KEY=<key>

# Windows:
setx OPENAI_API_BASE https://api.claudexia.tech/v1
setx OPENAI_API_KEY <key>
# ... restart shell after setx commands
```

Start working with aider and Claudexia on your codebase:

```bash
# Change directory into your codebase
cd /to/your/project

# Claude Opus 4.7
aider --model openai/claude-opus-4-7

# Claude Sonnet 4.6
aider --model openai/claude-sonnet-4-6

# Claude Haiku 4.5
aider --model openai/claude-haiku-4-5

# GPT-5.5
aider --model openai/gpt-5.5
```

See the [model warnings](warnings.html) section for information on warnings
which will occur when working with models that aider is not familiar with.
