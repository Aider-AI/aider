
# Aider can connect to most LLMs

[![connecting to many LLMs](/assets/llms.jpg)](https://aider.chat/assets/llms.jpg)

Aider works best with [GPT-4 Turbo](#openai) and [Claude 3 Opus](#anthropic),
as they are the very best models for editing code.
Aider also works quite well with [GPT-3.5](#openai).

To use aider with a *free* API provider, you can use [Groq's Llama 3 70B](#llama3)
which is comparable to GPT-3.5 in code editing performance.
Cohere also offers free API access to their [Command-R+ model](#cohere),
which works with aider
as a *very basic* coding assistant.

Aider supports connecting to almost any LLM,
but it may not work well with some models depending on their capabilities.
For example, GPT-3.5 is just barely capable of reliably *editing code* to provide aider's
interactive "pair programming" style workflow.
So you should expect that models which are less capable than GPT-3.5 may struggle to perform well with aider.

## Configuring models for aider

- [OpenAI](#openai)
- [Anthropic](#anthropic)
- [Llama3](#groq)
- [Cohere](#cohere)
- [Azure](#azure)
- [OpenRouter](#openrouter)
- [OpenAI compatible APIs](#openai-compatible-apis)
- [Other LLMs](#other-llms)
- [Model warnings](#model-warnings)
- [Editing format](#editing-format)

## OpenAI

To work with OpenAI's models, you need to provide your
[OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key)
either in the `OPENAI_API_KEY` environment variable or
via the `--openai-api-key` command line switch.

Aider has some built in shortcuts for the most popular OpenAI models and
has been tested and benchmarked to work well with them:

```
export OPENAI_API_KEY=<your-key-goes-here>

# GPT-4 Turbo is used by default
aider

# GPT-4 Turbo with Vision
aider --4-turbo-vision

# GPT-3.5 Turbo
aider --35-turbo
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
export ANTHROPIC_API_KEY=<your-key-goes-here>

# Claude 3 Opus
aider --opus

# Claude 3 Sonnet
aider --sonnet
```

You can use `aider --model <model-name>` to use any other Anthropic model.
For example, if you want to use a specific version of Opus
you could do `aider --model claude-3-opus-20240229`.

## GROQ

Groq currently offers *free* API access to the models they host.
The Llama 3 70B model works
well with aider and is comparable to GPT-3.5 in code editing performance.


To use **Llama3 70B**:

```
export GROQ_API_KEY=<your-key-goes-here>
aider --model groq/llama3-70b-8192
```

## Cohere

Cohere offers *free* API access to their models.
Their Command-R+ model works well with aider
as a *very basic* coding assistant.

To use **Command-R+**:

```
export COHERE_API_KEY=<your-key-goes-here>
aider --model command-r-plus
```

## Azure

Aider can be configured to connect to the OpenAI models on Azure.

```
export AZURE_API_KEY=<your-key-goes-here>
export AZURE_API_VERSION=2023-05-15
export AZURE_API_BASE=https://example-endpoint.openai.azure.com
aider --model azure/<your_deployment_name>
```

## OpenRouter

Aider can connect to models provided by OpenRouter:

```
export OPENROUTER_API_KEY=<your-key-goes-here>

# Llama3 70B instruct
aider --model openrouter/meta-llama/llama-3-70b-instruct

# Or any other open router model
aider --model openrouter/<provider>/<model>
```

## OpenAI compatible APIs

Aider can connect to any LLM which is accessible via an OpenAI compatible API endpoint.
Use `--openai-api-base` or set the `OPENAI_API_BASE`
environment variable to have aider connect to it.

```
export OPENAI_API_BASE=<your-endpoint-goes-here>
export OPENAI_API_KEY=<your-key-goes-here-if-required>
aider --model <model-name>
```

See the [Model warnings](#model-warnings)
section for information on warnings which will occur
when working with models that aider is not familiar with.

## Other LLMs

Aider uses the [litellm](https://docs.litellm.ai/docs/providers) package
to connect to hundreds of other models.
You can use `aider --model <model-name>` to use any supported model.

To explore the list of supported models you can run `aider --model <model-name>`
with a partial model name.
If the supplied name is not an exact match for a known model, aider will
return a list of possible matching models.
For example:

```
$ aider --model turbo

Unknown model turbo, did you mean one of these?
- gpt-4-turbo-preview
- gpt-4-turbo
- gpt-4-turbo-2024-04-09
- gpt-3.5-turbo
- gpt-3.5-turbo-0301
...
```

Depending on which model you access, you may need to provide an API key
or other configuration parameters by setting environment variables.
If any required variables are not set, aider will print an
error message listing which parameters are needed.

See the [list of providers supported by litellm](https://docs.litellm.ai/docs/providers)
for more details.

## Model warnings

On startup, aider tries to sanity check that it is configured correctly
to work with the specified models:

- It checks to see that all required environment variables are set for the model. These variables are required to configure things like API keys, API base URLs, etc.
- It checks a metadata database to look up the context window size and token costs for the model.

Sometimes one or both of these checks will fail, so aider will issue
some of the following warnings.

##### Missing environment variables

You need to set the listed variables.
Otherwise you will get error messages when you attempt to chat with the model.

```
Model azure/gpt-4-turbo: Missing these environment variables:
- AZURE_API_BASE
- AZURE_API_VERSION
- AZURE_API_KEY
```

##### Unknown which environment variables are required

Aider is unable verify the environment because it doesn't know
which variables are required for the model.
If required variables are missing,
you may get errors when you attempt to chat with the model.
You can look in the
[litellm provider documentation](https://docs.litellm.ai/docs/providers)
to see if the required variables are listed there.
```
Model gpt-5: Unknown which environment variables are required.
```


##### Unknown model, did you mean?

If you specify a model that aider has never heard of, you will get an
"unknown model" warning.

In this case, aider won't have normal metadata available like
the context window size, token costs, etc.
Some minor functionality will be limited when using such models, but
it's not really a significant problem.

Aider will also try to suggest similarly named models,
in case you made a typo or mistake when specifying the model name.

```
Model gpt-5: Unknown model, context window size and token costs unavailable.
Did you mean one of these?
- gpt-4
```




## Editing format

Aider uses 3 different "edit formats" to collect code edits from different LLMs:

- `whole` is a "whole file" editing format, where the model edits a file by returning a full new copy of the file with any changes included.
- `diff` is a more efficient diff style format, where the model specifies blocks of code to search and replace in order to made changes to files.
- `udiff` is the most efficient editing format, where the model returns unified diffs to apply changes to the file.

Different models work best with different editing formats.
Aider is configured to use the best edit format for all the popular OpenAI and Anthropic models.

For lesser known models aider will default to using the "whole" editing format.
If you would like to experiment with the more advanced formats, you can
use these switches: `--edit-format diff` or `--edit-format udiff`.
