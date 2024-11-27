---
title: Prompt caching
highlight_image: /assets/prompt-caching.jpg
parent: Usage
nav_order: 750
description: Aider supports prompt caching for cost savings and faster coding.

---

# Prompt caching

Aider supports prompt caching for cost savings and faster coding.
Currently Anthropic provides caching for Sonnet and Haiku,
and DeepSeek provides caching for Coder.

Aider organizes the chat history to try and cache:

- The system prompt.
- Read only files added with `--read` or `/read-only`.
- The repository map.
- The editable files that have been added to the chat.

![Prompt caching](/assets/prompt-caching.jpg)


## Usage

Run aider with `--cache-prompts` or add that setting to your 
[configuration files](/docs/config.html).

Due to limitations in the provider APIs, caching statistics and costs
are not available when streaming responses.
To turn off streaming, use `--no-stream`.

When caching is enabled, it will be noted for the main model when aider launches:

```
Main model: claude-3-5-sonnet-20240620 with diff edit format, prompt cache, infinite output
```

## Preventing cache expiration

Aider can ping the provider to keep your prompt cache warm and prevent
it from expiring.
By default, Anthropic keeps your cache for 5 minutes.
Use `--cache-keepalive-pings N` to tell aider to ping
every 5 minutes to keep the cache warm.
Aider will ping up to `N` times over a period of `N*5` minutes
after each message you send.


