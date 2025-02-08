---
title: Connecting to LLMs
nav_order: 40
has_children: true
description: Aider can connect to most LLMs for AI pair programming.
---

# Aider can connect to most LLMs
{: .no_toc }

[![connecting to many LLMs](/assets/llms.jpg)](https://aider.chat/assets/llms.jpg)


## Best models
{: .no_toc }

Aider works best with these models, which are skilled at editing code:

- [DeepSeek R1 and V3](/docs/llms/deepseek.html)
- [Claude 3.5 Sonnet](/docs/llms/anthropic.html)
- [OpenAI o1, o3-mini and GPT-4o](/docs/llms/openai.html)


## Free models
{: .no_toc }

Aider works with a number of **free** API providers:

- Google's [Gemini 1.5 Pro](/docs/llms/gemini.html) works with aider, with
code editing capabilities similar to GPT-3.5.
- You can use [Llama 3 70B on Groq](/docs/llms/groq.html) which is comparable to GPT-3.5 in code editing performance.
- Cohere also offers free API access to their [Command-R+ model](/docs/llms/cohere.html), which works with aider as a *very basic* coding assistant.

## Local models
{: .no_toc }

Aider can work also with local models, for example using [Ollama](/docs/llms/ollama.html).
It can also access
local models that provide an
[Open AI compatible API](/docs/llms/openai-compat.html).

## Use a capable model
{: .no_toc }

Check
[Aider's LLM leaderboards](https://aider.chat/docs/leaderboards/)
to see which models work best with aider.

Be aware that aider may not work well with less capable models.
If you see the model returning code, but aider isn't able to edit your files
and commit the changes...
this is usually because the model isn't capable of properly
returning "code edits".
Models weaker than GPT 3.5 may have problems working well with aider.

