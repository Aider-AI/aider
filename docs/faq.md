
# Frequently asked questions

## Can I use aider with other LLMs, local LLMs, etc?

Aider does not officially support use with LLMs other than OpenAI's gpt-3.5-turbo and gpt-4
and their variants.

It generally requires some model-specific tuning to get prompts and
editing formats working well. For example, GPT-3.5 and GPT-4 use very
different prompts and editing formats in aider right now. 
Adopting new LLMs will probably require a similar effort to tailor the
prompting and edit formats.

That said, aider does provide some features to experiment with other models.
If you can make the model accessible via an OpenAI compatible API,
you can use `--openai-api-base` to connect to a different API endpoint.

Here is are some
[GitHub issues which may contain relevant information](https://github.com/paul-gauthier/aider/issues?q=is%3Aissue+%22openai-api-base%22+).

[LocalAI](https://github.com/go-skynet/LocalAI)
looks like a relevant tool to serve many local models via a compatible API:


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


## How do I get ctags working?

First, be aware that ctags is completely optional and not required to use aider.

If you wish to use ctags, you should consult the
[universal ctags repo](https://github.com/universal-ctags/ctags)
for official instructions on how to install it in your environment.
You may be able to install a compatible version using these commands:

* Mac: `brew install universal-ctags`
* Windows: `choco install universal-ctags`
* Ubuntu: `sudo apt-get install universal-ctags`

Some things to be aware of:

* The `ctags` command needs to be on your shell path so that it will run by default when aider invokes `ctags ...`.
* You need a build which includes the json feature. You can check by running `ctags --version` and looking for `+json` in the `Optional compiled features` list.



