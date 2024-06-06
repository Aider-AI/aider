---
parent: Connecting to LLMs
nav_order: 200
---

# Anthropic

To work with Anthropic's models, you need to provide your
[Anthropic API key](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
either in the `ANTHROPIC_API_KEY` environment variable or
via the `--anthropic-api-key` command line switch.

Aider has some built in shortcuts for the most popular Anthropic models and
has been tested and benchmarked to work well with them:

```
pip install aider-chat

export ANTHROPIC_API_KEY=<key> # Mac/Linux
setx   ANTHROPIC_API_KEY <key> # Windows

# Claude 3 Opus
aider --opus

# Claude 3 Sonnet
aider --sonnet

# List models available from Anthropic
aider --models anthropic/
```

You can use `aider --model <model-name>` to use any other Anthropic model.
For example, if you want to use a specific version of Opus
you could do `aider --model claude-3-opus-20240229`.
