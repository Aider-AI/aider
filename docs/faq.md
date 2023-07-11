
# Frequently asked questions

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
