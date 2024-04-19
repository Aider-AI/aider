
# Connecting aider to LLMs

Aider works well with OpenAI's GPT 3.5, GPT-4, GPT-4 Turbo with Vision and
Anthropic's Claude 3 Opus and Sonnet.

GPT-4 Turbo and Claude 3 Opus are recommended for the best results.

Aider also has support for connecting to almost any LLM, but may not be as effective
depending on the capabilities of the model.
For comparison, GPT-3.5 is just barely capable of *editing code* to provide aider's
interactive "pair programming" style workflow.
Models that are less capable than GPT-3.5 may struggle to perform well with aider.

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

If you can make an LLM accessible via an OpenAI compatible API,
you can use `--openai-api-base` to connect to a different API endpoint.

## Other LLMs

Aider uses the [litellm](https://docs.litellm.ai/docs/providers) package
to connect to hundreds of other models.
You can use `aider --model <model-name>` to use any supported model.

To explore the list of supported models you can run `aider --model <name>`.
If it's not an exact match for a model, aider will
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
or other configuration parameters by setting certain environment variables.
If any required variables are not set, aider will print an
error message listing which parameters are needed.

Or, see the [list of providers supported by litellm](https://docs.litellm.ai/docs/providers)
for more details.

