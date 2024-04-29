
# Aider can connect to most LLMs

[![connecting to many LLMs](/assets/llms.jpg)](https://aider.chat/assets/llms.jpg)

## Best models

**Aider works best with [GPT-4 Turbo](#openai) and [Claude 3 Opus](#anthropic),**
as they are the very best models for editing code.
Aider also works quite well with [GPT-3.5](#openai).

## Free models

**Aider works with a number of free API providers.**
Google's [Gemini 1.5 Pro](#gemini) is
the most capable free model to use with aider, with
code editing capabilities similar to GPT-3.5.
You can use [Llama 3 70B on Groq](#llama3)
which is comparable to GPT-3.5 in code editing performance.
Cohere also offers free API access to their [Command-R+ model](#cohere),
which works with aider
as a *very basic* coding assistant.

## Local models

Aider can work also with local models, for example using [Ollama](#ollama).

## Other models

Aider supports connecting to almost any LLM,
but it may not work well with some models depending on their capabilities.
For example, GPT-3.5 is just barely capable of reliably *editing code* to provide aider's
interactive "pair programming" style workflow.
So you should expect that models which are less capable than GPT-3.5 may struggle to perform well with aider.

## Configuring models

- [OpenAI](#openai)
- [Anthropic](#anthropic)
- [Gemini](#gemini)
- [Groq & Llama3](#groq)
- [Cohere](#cohere)
- [Azure](#azure)
- [OpenRouter](#openrouter)
- [Ollama](#ollama)
- [OpenAI compatible APIs](#openai-compatible-apis)
- [Other LLMs](#other-llms)
- [Model warnings](#model-warnings)
- [Editing format](#editing-format)

Aider uses the LiteLLM package to connect to LLM providers.
The [LiteLLM provider docs](https://docs.litellm.ai/docs/providers)
contain more detail on all the supported providers,
their models and any required environment variables.

## OpenAI

To work with OpenAI's models, you need to provide your
[OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key)
either in the `OPENAI_API_KEY` environment variable or
via the `--openai-api-key` command line switch.

Aider has some built in shortcuts for the most popular OpenAI models and
has been tested and benchmarked to work well with them:

```
pip install aider-chat
export OPENAI_API_KEY=<your-key-goes-here>

# GPT-4 Turbo is used by default
aider

# GPT-4 Turbo with Vision
aider --4-turbo-vision

# GPT-3.5 Turbo
aider --35-turbo

# List models available from OpenAI
aider --models openai/
```

You can use `aider --model <model-name>` to use any other OpenAI model.
For example, if you want to use a specific version of GPT-4 Turbo
you could do `aider --model gpt-4-0125-preview`.

## Anthropic

To work with Anthropic's models, you need to provide your
[Anthropic API key](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)
either in the `ANTHROPIC_API_KEY` environment variable or
via the `--anthropic-api-key` command line switch.

Aider has some built in shortcuts for the most popular Anthropic models and
has been tested and benchmarked to work well with them:

```
pip install aider-chat
export ANTHROPIC_API_KEY=<your-key-goes-here>

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

## Gemini

Google currently offers
[*free* API access to the Gemini 1.5 Pro model](https://ai.google.dev/pricing).
This is the most capable free model to use with aider,
with code editing capability that's comparable to GPT-3.5.
You'll need a [Gemini API key](https://aistudio.google.com/app/u/2/apikey).

```
pip install aider-chat
export GEMINI_API_KEY=<your-key-goes-here>
aider --model gemini/gemini-1.5-pro-latest

# List models available from Gemini
aider --models gemini/
```

## GROQ

Groq currently offers *free* API access to the models they host.
The Llama 3 70B model works
well with aider and is comparable to GPT-3.5 in code editing performance.
You'll need a [Groq API key](https://console.groq.com/keys).

To use **Llama3 70B**:

```
pip install aider-chat
export GROQ_API_KEY=<your-key-goes-here>
aider --model groq/llama3-70b-8192

# List models available from Groq
aider --models groq/
```


## Cohere

Cohere offers *free* API access to their models.
Their Command-R+ model works well with aider
as a *very basic* coding assistant.
You'll need a [Cohere API key](https://dashboard.cohere.com/welcome/login).

To use **Command-R+**:

```
pip install aider-chat
export COHERE_API_KEY=<your-key-goes-here>
aider --model command-r-plus

# List models available from Cohere
aider --models cohere_chat/
```

## Azure

Aider can connect to the OpenAI models on Azure.

```
pip install aider-chat
export AZURE_API_KEY=<your-key-goes-here>
export AZURE_API_VERSION=2023-05-15
export AZURE_API_BASE=https://example-endpoint.openai.azure.com
aider --model azure/<your_deployment_name>

# List models available from Azure
aider --models azure/
```

## OpenRouter

Aider can connect to [models provided by OpenRouter](https://openrouter.ai/models?o=top-weekly):
You'll need an [OpenRouter API key](https://openrouter.ai/keys).

```
pip install aider-chat
export OPENROUTER_API_KEY=<your-key-goes-here>

# Or any other open router model
aider --model openrouter/<provider>/<model>

# List models available from OpenRouter
aider --models openrouter/
```

In particular, Llama3 70B works well with aider, at low cost:

```
# Llama3 70B instruct
aider --model openrouter/meta-llama/llama-3-70b-instruct
```


## Ollama

Aider can connect to local Ollama models.

```
# Pull the model
ollama pull <MODEL>

# Start your ollama server
ollama serve

# In another terminal window
export OLLAMA_API_BASE=http://127.0.0.1:11434
aider --model ollama/<MODEL>
```

In particular, `llama3:70b` works very well with aider:


```
ollama pull llama3:70b
ollama serve

# ...in another terminal window...
export OLLAMA_API_BASE=http://127.0.0.1:11434
aider --model ollama/llama3:70b 
```

Also see the [model warnings](#model-warnings)
section for information on warnings which will occur
when working with models that aider is not familiar with.


## OpenAI compatible APIs

Aider can connect to any LLM which is accessible via an OpenAI compatible API endpoint.

```
pip install aider-chat
export OPENAI_API_BASE=<your-endpoint-goes-here>

# If your endpoint needs a key
export OPENAI_API_KEY=<your-key-goes-here>

# Prefix the model name with openai/
aider --model openai/<model-name>
```

See the [model warnings](#model-warnings)
section for information on warnings which will occur
when working with models that aider is not familiar with.

## Other LLMs

Aider uses the [litellm](https://docs.litellm.ai/docs/providers) package
to connect to hundreds of other models.
You can use `aider --model <model-name>` to use any supported model.

To explore the list of supported models you can run `aider --models <model-name>`
with a partial model name.
If the supplied name is not an exact match for a known model, aider will
return a list of possible matching models.
For example:

```
$ aider --models turbo

Aider v0.29.3-dev
Models which match "turbo":
- gpt-4-turbo-preview (openai/gpt-4-turbo-preview)
- gpt-4-turbo (openai/gpt-4-turbo)
- gpt-4-turbo-2024-04-09 (openai/gpt-4-turbo-2024-04-09)
- gpt-3.5-turbo (openai/gpt-3.5-turbo)
- ...
```

See the [list of providers supported by litellm](https://docs.litellm.ai/docs/providers)
for more details.

## Model warnings

On startup, aider tries to sanity check that it is configured correctly
to work with the specified models:

- It checks to see that all required environment variables are set for the model. These variables are required to configure things like API keys, API base URLs, etc.
- It checks a metadata database to look up the context window size and token costs for the model.

Sometimes one or both of these checks will fail, so aider will issue
some of the following warnings.

#### Missing environment variables

```
Model azure/gpt-4-turbo: Missing these environment variables:
- AZURE_API_BASE
- AZURE_API_VERSION
- AZURE_API_KEY
```

You need to set the listed environment variables.
Otherwise you will get error messages when you start chatting with the model.


#### Unknown which environment variables are required

```
Model gpt-5: Unknown which environment variables are required.
```

Aider is unable verify the environment because it doesn't know
which variables are required for the model.
If required variables are missing,
you may get errors when you attempt to chat with the model.
You can look in the
[litellm provider documentation](https://docs.litellm.ai/docs/providers)
to see if the required variables are listed there.

#### Unknown model, did you mean?

```
Model gpt-5: Unknown model, context window size and token costs unavailable.
Did you mean one of these?
- gpt-4
```

If you specify a model that aider has never heard of, you will get an
"unknown model" warning.
This means aider doesn't know the context window size and token costs
for that model.
Some minor functionality will be limited when using such models, but
it's not really a significant problem.

Aider will also try to suggest similarly named models,
in case you made a typo or mistake when specifying the model name.


## Editing format

Aider uses 3 different "edit formats" to collect code edits from different LLMs:

- `whole` is a "whole file" editing format, where the model edits a file by returning a full new copy of the file with any changes included.
- `diff` is a more efficient diff style format, where the model specifies blocks of code to search and replace in order to made changes to files.
- `udiff` is the most efficient editing format, where the model returns unified diffs to apply changes to the file.

Different models work best with different editing formats.
Aider is configured to use the best edit format for the popular OpenAI and Anthropic models and the other models recommended on this page. 

For lesser known models aider will default to using the "whole" editing format.
If you would like to experiment with the more advanced formats, you can
use these switches: `--edit-format diff` or `--edit-format udiff`.
