---
parent: Installation
nav_order: 10
---

# Installing aider
{: .no_toc }

- TOC
{:toc}

## Install git

Make sure you have git installed.
Here are
[instructions for installing git in various environments](https://github.com/git-guides/install-git).

## Get your API key

To work with OpenAI's GPT 3.5 or GPT-4 models you need a paid
[OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key).
Note that this is different than being a "ChatGPT Plus" subscriber.

To work with Anthropic's models like Claude 3 Opus you need a paid
[Anthropic API key](https://docs.anthropic.com/claude/reference/getting-started-with-the-api).

## Windows install

```
# Install aider
py -m pip install aider-chat

# To work with GPT-4o:
$ aider --openai-api-key sk-xxx...

# To work with Claude 3 Opus:
$ aider --anthropic-api-key sk-xxx... --opus
```

## Mac/Linux install

```
# Install aider
python -m pip install aider-chat

# To work with GPT-4o:
$ aider --openai-api-key sk-xxx...

# To work with Claude 3 Opus:
$ aider --anthropic-api-key sk-xxx... --opus
```

## Working with other LLMs

Aider works well with GPT-4o, Claude 3 Opus, GPT-3.5 and supports [connecting to almost any LLM](https://aider.chat/docs/llms.html).

## You are done!

There are some [optional install steps](/docs/install/optional.html) you could consider.
See the [usage instructions](https://aider.chat/docs/usage.html) to start coding with aider.

