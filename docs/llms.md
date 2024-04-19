
# Aider can connect to most LLMs

Aider works well with OpenAI's GPT 3.5, GPT-4, GPT-4 Turbo with Vision and
Anthropic's Claude 3 Opus and Sonnet.

GPT-4 Turbo and Claude 3 Opus are recommended for the best results.

Aider also has support for connecting to almost any LLM, but it may not work as well
depending on the capabilities of the model.
For context, GPT-3.5 is just barely capable of *editing code* to provide aider's
interactive "pair programming" style workflow.
Models that are less capable than GPT-3.5 may struggle to perform well with aider.

- [OpenAI](#openai)
- [Anthropic](#anthropic)
- [Azure](#azure)
- [OpenAI compatible APIs](#openai-compatible-apis)
- [Other LLMs](#other-llms)
- [Editing format](#editing-format)

## OpenAI

To work with OpenAI's models, you need to provide your
[OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key)
either in the `OPENAI_API_KEY` environment variable or
via the `--openai-api-key` command line switch.

Aider has some built in shortcuts for the most popular OpenAI models and
has been tested and benchmarked to work well with them:

- OpenAI's GPT-4 Turbo: run `aider` with no args uses GPT-4 Turbo by default.
- OpenAI's GPT-4 Turbo with Vision: run `aider --4-turbo-vision` to use this vision capable model, allowing you to share images with GPT by adding them to the chat with `/add` or by naming them on the command line.
- OpenAI's GPT-3.5 Turbo: Run `aider --35-turbo`.

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

- Anthropic's Claude 3 Opus: `aider --opus`
- Anthropic's Claude 3 Sonnet: `aider --sonnet`

You can use `aider --model <model-name>` to use any other Anthropic model.
For example, if you want to use a specific version of Opus
you could do `aider --model claude-3-opus-20240229`.

## Azure

Aider can be configured to connect to the OpenAI models on Azure.
You can run aider with the following arguments to connect to Azure:

```
$ aider \
    --openai-api-type azure \
    --openai-api-key your-key-goes-here \
    --openai-api-base https://example-endpoint.openai.azure.com \
    --openai-api-version 2023-05-15 \
    --openai-api-deployment-id deployment-name \
    ...
```

You could also store those values in an `.aider.conf.yml` file in your home directory:

```
openai-api-type: azure
openai-api-key: your-key-goes-here
openai-api-base: https://example-endpoint.openai.azure.com
openai-api-version: 2023-05-15
openai-api-deployment-id: deployment-name
```

Or you can populate the following environment variables instead:

```
OPENAI_API_TYPE=azure
OPENAI_API_KEY=your-key-goes-here
OPENAI_API_BASE=https://example-endpoint.openai.azure.com
OPENAI_API_VERSION=2023-05-15
OPENAI_API_DEPLOYMENT_ID=deployment-name
```

See the
[official Azure documentation on using OpenAI models](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/chatgpt-quickstart?tabs=command-line&pivots=programming-language-python)
for more information on how to populate the above configuration values.

## OpenAI compatible APIs

If you can make an LLM accessible via an OpenAI compatible API endpoint,
you can use `--openai-api-base` to have aider connect to it.

You might need to use `--no-require-model-info` if aider doesn't
recognize the model you want to use.
For unknown models, aider won't have normal metadata available like
the context window size, token costs, etc.
Some minor functionality will be limited when using such models.

## Other LLMs

Aider uses the [litellm](https://docs.litellm.ai/docs/providers) package
to connect to hundreds of other models.
You can use `aider --model <model-name>` to use any supported model.

To explore the list of supported models you can run `aider --model <name>`.
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


## Editing format

Aider uses 3 different "edit formats" to collect code edits from different LLMs:

- `whole` is a "whole file" editing format, where the model edits a file by returning a full new copy of the file with any changes included.
- `diff` is a more efficient diff style format, where the model specified blocks of code to search and replace in order to made changes to files.
- `udiff` is the most efficient editing format, where the model returns unified diffs to apply changes to the file.

Different models work best with different editing formats.
Aider is configured to use the best edit format for all the popular OpenAI and Anthropic models.

For lesser known models aider will default to using the "whole" editing format.
If you would like to experiment with the more advanced formats, you can
use these switches: `--edit-format diff` or `--edit-format udiff`.
