
# Frequently asked questions

## GPT-4 vs GPT-3.5

Aider supports all of OpenAI's chat models.
You can choose a model with the `--model` command line argument.
For a discussion of using other non-OpenAI models, see the
[FAQ](#can-i-use-aider-with-other-llms-local-llms-etc).

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

## Can I use aider with other LLMs, local LLMs, etc?

Aider does not officially support use with LLMs other than OpenAI's gpt-3.5-turbo and gpt-4
and their variants.

It seems to require model-specific tuning to get prompts and
editing formats working well with a new model. For example, GPT-3.5 and GPT-4 use very
different prompts and editing formats in aider right now.
Adopting new LLMs will probably require a similar effort to tailor the
prompting and edit formats.

That said, aider does provide some features to experiment with other models.
If you can make the model accessible via an OpenAI compatible API,
you can use `--openai-api-base` to connect to a different API endpoint.

Here are some
[GitHub issues which may contain relevant information](https://github.com/paul-gauthier/aider/issues?q=is%3Aissue+%22openai-api-base%22+).

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
