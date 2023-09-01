
# Frequently asked questions

- [How does aider use git?](#how-does-aider-use-git)
- [GPT-4 vs GPT-3.5](#gpt-4-vs-gpt-35)
- [Aider isn't editing my files?](#aider-isnt-editing-my-files)
- [Accessing other LLMs with OpenRouter](#accessing-other-llms-with-openrouter)
- [Can I use aider with other LLMs, local LLMs, etc?](#can-i-use-aider-with-other-llms-local-llms-etc)
- [Can I change the system prompts that aider uses?](#can-i-change-the-system-prompts-that-aider-uses)
- [Can I run aider in Google Colab?](#can-i-run-aider-in-google-colab)

## How does aider use git?

Aider works best with code that is part of a git repo.
Aider is tightly integrated with git, which makes it easy to:

  - Undo any GPT changes that you don't like
  - Go back later to review the changes GPT made to your code
  - Manage a series of GPT's changes on a git branch

Aider specifically uses git in these ways:
 
  - It asks to create a git repo if you launch it in a directory without one.
  - Whenever GPT edits a file, aider commits those changes with a descriptive commit message. This makes it easy to undo or review GPT's changes.
  - Aider takes special care if GPT tries to edit files that already have uncommitted changes (dirty files). Aider will first commit any preexisting changes with a descriptive commit message. This keeps your edits separate from GPT's edits, and makes sure you never lose your work if GPT makes an inappropriate change.
  
Aider also allows you to use in-chat commands to `/diff` or `/undo` the last change made by GPT.
To do more complex management of your git history, you cat use raw `git` commands,
either by using `/git` within the chat, or with standard git tools outside of aider.

While it is not recommended, you can disable aider's use of git in a few ways:

  - `--no-auto-commits` will stop aider from git committing each of GPT's changes.
  - `--no-dirty-commits` will stop aider from committing dirty files before applying GPT's edits.
  - `--no-git` will completely stop aider from using git on your files. You should ensure you are keeping sensible backups of the files you are working with.

### How did v0.13.0 change git usage?

As of v0.13.0, aider works with git in a more streamlined manner.
Previously, aider would *always* prompt you
if it noticed that you had uncommitted changes *anywhere* in your repo.

Now aider only pays attention to uncommitted changes in files
that GPT attempts to edit.
And aider doesn't interrupt you, it simply commits your pending
changes before applying GPT's edits.
This keeps your edits separate from GPT's edits, and
makes sure you never lose your work if GPT makes an inappropriate change.

## GPT-4 vs GPT-3.5

Aider supports all of OpenAI's chat models.
You can choose a model with the `--model` command line argument.

You will probably get the best results with one of the GPT-4 models.
They have large context windows, better coding skills and
they generally obey the instructions in the system prompt.
GPT-4 is able to structure code edits as simple "diffs"
and use a
[repository map](https://aider.chat/docs/ctags.html)
to improve its ability to make changes in larger codebases.

GPT-3.5 is supported more experimentally
and is limited to editing somewhat smaller codebases.
It is less able to follow instructions and
can't reliably return code edits as "diffs".
Aider disables the
repository map
when using GPT-3.5.

For a detailed and quantitative comparison, please see the
[code editing benchmark results for GPT-3.5 and GPT-4](https://aider.chat/docs/benchmarks.html).

In practice, this means you can use aider to edit a set of source files
that total up to the sizes below.
Just add the specific set of files to the chat
that are relevant to the change you are requesting.
This minimizes your use of the context window, as well as costs.

| Model             | Context<br>Size | Edit<br>Format | Max<br>File Size | Max<br>File Size | Repo<br>Map? |
| ----------------- | -- | --     | -----| -- | -- |
| gpt-3.5-turbo     |  4k tokens | whole file | 2k tokens | ~8k bytes | no |
| gpt-3.5-turbo-16k | 16k tokens | whole file | 8k tokens | ~32k bytes | no |
| gpt-4             |  8k tokens | diffs | 8k tokens | ~32k bytes | yes |
| gpt-4-32k         | 32k tokens | diffs | 32k tokens  | ~128k bytes | yes |

## Aider isn't editing my files?

Sometimes GPT will reply with some code changes that don't get applied to your local files.
In these cases, aider might say something like "Failed to apply edit to *filename*".

This usually happens because GPT is not specifying the edits
to make in the format that aider expects.
GPT-3.5 is especially prone to disobeying the system prompt instructions in this manner, but it also happens with GPT-4.

Aider makes every effort to get GPT to conform, and works hard to deal with
replies that are "almost" correctly formatted.
If Aider detects an improperly formatted reply, it gives GPT feedback to try again.
Also, before each release new versions of aider are
[benchmarked](https://aider.chat/docs/benchmarks.html).
This helps prevent regressions in the code editing
performance of GPT that could have been inadvertantly
introduced.

But sometimes GPT just won't cooperate.
In these cases, here are some things you might try:

  - Just ask it to try again. Explain the problem with the response if you can. Here is some suggested language which will be familiar to GPT based on its system prompt.
    - With GPT-3.5, you could say something like "Send me back the new code as a properly formatted **file listing**".
    - With GPT-4, you could say something like "Format those code changes properly as an **edit block**".
    - "Don't skip code and replace it with comments, send me back all the code!"
    - Etc...
  - Use `/drop` to remove files from the chat session which aren't needed for the task at hand. This will reduce distractions and may help GPT produce properly formatted edits.
  - Use `/clear` to remove the conversation history, again to help GPT focus.

## Accessing other LLMs with OpenRouter

[OpenRouter](https://openrouter.ai) provide an interface to [many models](https://openrouter.ai/docs) which are not widely accessible, in particular gpt-4-32k and claude-2.

To access the openrouter models simply

- register for an account, purchase some credits and generate an api key
- set --openai-api-base to https://openrouter.ai/api/v1
- set --openai-api-key to your openrouter key
- set --model to the model of your choice (openai/gpt-4-32k, anthropic/claude-2 etc.)

Some of the models weren't very functional and each llm has its own quirks. The anthropic models work ok, but the llama-2 ones in particular will need more work to play friendly with aider.

## Can I use aider with other LLMs, local LLMs, etc?

Aider provides experimental support for LLMs other than OpenAI's GPT-3.5 and GPT-4. The support is currently only experimental for two reasons:

- GPT-3.5 is just barely capable of *editing code* to provide aider's interactive "pair programming" style workflow. None of the other models seem to be as capable as GPT-3.5 yet.
- Just "hooking up" aider to a new model by connecting to its API is almost certainly not enough to get it working in a useful way. Getting aider working well with GPT-3.5 and GPT-4 was a significant undertaking, involving [specific code editing prompts and backends for each model and extensive benchmarking](https://aider.chat/docs/benchmarks.html). Officially supporting each new LLM will probably require a similar effort to tailor the prompts and editing backends.

Numerous users have done experiments with numerous models. None of these experiments have yet identified other models that look like they are capable of working well with aider.

Once we see signs that a *particular* model is capable of code editing, it would be reasonable for aider to attempt to officially support such a model. Until then, aider will simply maintain experimental support for using alternative models.

There are ongoing discussions about [LLM integrations in the aider discord](https://discord.com/channels/1131200896827654144/1133060780649087048).

Here are some [GitHub issues which may contain relevant information](https://github.com/paul-gauthier/aider/issues?q=is%3Aissue+%23172).

### OpenAI API compatible LLMs

If you can make the model accessible via an OpenAI compatible API,
you can use `--openai-api-base` to connect to a different API endpoint.

### Local LLMs

[LocalAI](https://github.com/go-skynet/LocalAI)
and
[SimpleAI](https://github.com/lhenault/simpleAI)
look like relevant tools to serve local models via a compatible API.


### Azure

Aider can be configured to connect to the OpenAI models on Azure.
Aider supports the configuration changes specified in the
[official openai python library docs](https://github.com/openai/openai-python#microsoft-azure-endpoints).
You should be able to run aider with the following arguments to connect to Azure:

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

See the
[official Azure documentation on using OpenAI models](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/chatgpt-quickstart?tabs=command-line&pivots=programming-language-python)
for more information on how to populate the above configuration values.




## Can I change the system prompts that aider uses?

Aider is set up to support different system prompts and edit formats
in a modular way. If you look in the `aider/coders` subdirectory, you'll
see there's a base coder with base prompts, and then there are
a number of
different specific coder implementations.

If you're thinking about experimenting with system prompts
this document about
[benchmarking GPT-3.5 and GPT-4 on code editing](https://aider.chat/docs/benchmarks.html)
might be useful background.

While it's not well documented how to add new coder subsystems, you may be able
to modify an existing implementation or use it as a template to add another.

To get started, try looking at and modifying these files.

The wholefile coder is currently used by GPT-3.5 by default. You can manually select it with `--edit-format whole`.

- wholefile_coder.py
- wholefile_prompts.py

The editblock coder is currently used by GPT-4 by default. You can manually select it with `--edit-format diff`.

- editblock_coder.py
- editblock_prompts.py

When experimenting with coder backends, it helps to run aider with `--verbose --no-pretty` so you can see
all the raw information being sent to/from GPT in the conversation.

## Can I run aider in Google Colab?

User [imabutahersiddik](https://github.com/imabutahersiddik)
has provided this
[Colab notebook](https://colab.research.google.com/drive/1J9XynhrCqekPL5PR6olHP6eE--rnnjS9?usp=sharing).
