---
title: Connecting to LLMs
nav_order: 70
has_children: true
---

# Aider can connect to most LLMs
{: .no_toc }

[![connecting to many LLMs](/assets/llms.jpg)](https://aider.chat/assets/llms.jpg)

## Best models
{: .no_toc }

**Aider works best with [GPT-4o](#openai) and [Claude 3 Opus](#anthropic),**
as they are the very best models for editing code.

## Free models
{: .no_toc }

Aider works with a number of **free** API providers:

- Google's [Gemini 1.5 Pro](#gemini) is the most capable free model to use with aider, with
code editing capabilities similar to GPT-3.5.
- You can use [Llama 3 70B on Groq](#groq) which is comparable to GPT-3.5 in code editing performance.
- The [Deepseek Chat v2](#deepseek) model work well with aider, better than GPT-3.5. Deepseek currently offers 5M free tokens of API usage.
- Cohere also offers free API access to their [Command-R+ model](#cohere), which works with aider as a *very basic* coding assistant.

## Local models
{: .no_toc }

Aider can work also with local models, for example using [Ollama](#ollama).
It can also access
local models that provide an
[Open AI compatible API](#openai-compatible-apis).

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

# Using a .env file

Aider will read environment variables from a `.env` file in
root of your git repo or in current directory.
You can give it an explicit file to load with the `--env-file <filename>` parameter.

You can use a `.env` file to store various keys and other settings for the
models you use with aider.

Here is an example `.env` file:

```
OPENAI_API_KEY=<key>
ANTHROPIC_API_KEY=<key>
GROQ_API_KEY=<key>
OPENROUTER_API_KEY=<key>

AZURE_API_KEY=<key>
AZURE_API_VERSION=2023-05-15
AZURE_API_BASE=https://example-endpoint.openai.azure.com

OLLAMA_API_BASE=http://127.0.0.1:11434
```





