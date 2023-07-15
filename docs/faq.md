
# Frequently asked questions

## How does aider use git?

It is recommended that you use aider with code that is part of a git repo.
This allows aider to maintain the safety of your code. Using git makes it easy to:

  - Review the changes GPT made to your code
  - Undo changes that weren't appropriate
  - Manage a series of GPT's changes on a git branch
  - etc

Working without git means that GPT might drastically change your code without an easy way to undo the changes.

Aider tries to provide safety using git in a few ways:

  - It asks to create a git repo if you launch it in a directory without one.
  - When you add a file to the chat, aider asks permission to add it to the git repo if needed.
  - At launch and before sending requests to GPT, aider checks if the repo is dirty and offers to commit those changes for you. This way, the GPT changes will be applied to a clean repo and won't be intermingled with your own changes.
  - After GPT changes your code, aider commits those changes with a descriptive commit message.

Aider also allows you to use in-chat commands to `/diff` or `/undo` the last change made by GPT.
To do more complex management of your git history, you should use `git` on the command line outside of aider.
You can start a branch before using aider to make a sequence of changes.
Or you can `git reset` a longer series of aider changes that didn't pan out. Etc.

While it is not recommended, you can disable aider's use of git in a few ways:

  - `--no-auto-commits` will stop aider from git committing each of GPT's changes.
  - `--no-dirty-commits` will stop aider from ensuring your repo is clean before sending requests to GPT.
  - `--no-git` will completely stop aider from using git on your files. You should ensure you are keeping sensible backups of the files you are working with.


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

## Can I use aider with other LLMs, local LLMs, etc?

Aider does not officially support use with LLMs other than OpenAI's gpt-3.5-turbo and gpt-4
and their variants.

It seems to require model-specific tuning to get prompts and
editing formats working well with a new model. For example, GPT-3.5 and GPT-4 use very
different prompts and editing formats in aider right now.
Adopting new LLMs will probably require a similar effort to tailor the
prompting and edit formats.

That said, aider does provide some features to experiment with other models.

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

### Other LLMs

If you can make the model accessible via an OpenAI compatible API,
you can use `--openai-api-base` to connect to a different API endpoint.

Here are some
[GitHub issues which may contain relevant information](https://github.com/paul-gauthier/aider/issues?q=is%3Aissue+%22openai-api-base%22+).

### Local LLMs

[LocalAI](https://github.com/go-skynet/LocalAI)
and
[SimpleAI](https://github.com/lhenault/simpleAI)
look like relevant tools to serve local models via a compatible API:




## Can I change the system prompts that aider uses?

Aider is set up to support different system prompts and edit formats
in a modular way. If you look in the `aider/coders` subdirectory, you'll
see there's a base coder with base prompts, and then there are
a number of
different specific coder implementations.

While it's not yet documented how to add new coder subsystems, you may be able
to modify an existing implementation or use it as a template to add another.

If you're thinking about experimenting with system prompts
this document about
[benchmarking GPT-3.5 and GPT-4 on code editing](https://aider.chat/docs/benchmarks.html)
might be useful background.

## Can I run aider in Google Colab?

User [imabutahersiddik](https://github.com/imabutahersiddik)
has provided this
[Colab notebook](https://colab.research.google.com/drive/1J9XynhrCqekPL5PR6olHP6eE--rnnjS9?usp=sharing).
