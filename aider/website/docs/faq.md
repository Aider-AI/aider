---
nav_order: 90
description: Frequently asked questions about aider.
---

# FAQ
{: .no_toc }

- TOC
{:toc}

{% include help-tip.md %}

## How can I add ALL the files to the chat?

People regularly ask about how to add **many or all of their repo's files** to the chat.
This is probably not a good idea and will likely do more harm than good.

The best approach is think about which files need to be changed to accomplish
the task you are working on. Just add those files to the chat.

Usually when people want to add "all the files" it's because they think it
will give the LLM helpful context about the overall code base.
Aider will automatically give the LLM a bunch of additional context about
the rest of your git repo.
It does this by analyzing your entire codebase in light of the
current chat to build a compact
[repository map](https://aider.chat/2023/10/22/repomap.html).

Adding a bunch of files that are mostly irrelevant to the
task at hand will often distract or confuse the LLM.
The LLM will give worse coding results, and sometimese even fail to correctly edit files.
Addings extra files will also increase the token costs on your OpenAI invoice.

Again, it's usually best to just add the files to the chat that will need to be modified.
If you still wish to add lots of files to the chat, you can:

- Use a wildcard when you launch aider: `aider src/*.py`
- Use a wildcard with the in-chat `/add` command: `/add src/*.py`
- Give the `/add` command a directory name and it will recurisvely add every file under that dir: `/add src`

## Can I use aider in a large (mono) repo?

Aider will work in any size repo, but is not optimized for quick
performance and response time in very large repos.
There are some things you can do to improve performance.

Change into a sub directory of your repo that contains the
code you want to work on and use the `--subtree-only` switch.
This will tell aider to ignore the repo outside of the
directory you start in.

You can also create a `.aiderignore` file to tell aider
to ignore parts of the repo that aren't relevant to your task.
This file conforms to `.gitignore` syntax and conventions.

You can use `--aiderignore <filename>` to name a specific file
to use for ignore patterns.
You might have a few of these handy for when you want to work on
frontend, backend, etc portions of your repo.

## How can I run aider locally from source code?

To run the project locally, follow these steps:

```
# Clone the repository:
git clone git@github.com:paul-gauthier/aider.git

# Navigate to the project directory:
cd aider

# It's recommended to make a virtual environment

# Install the dependencies listed in the `requirements.txt` file:
python -m pip install -e .

# Run the local version of Aider:
python -m aider
```




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

The editblock coder is currently used by GPT-4o by default. You can manually select it with `--edit-format diff`.

- editblock_coder.py
- editblock_prompts.py

The universal diff coder is currently used by GPT-4 Turbo by default. You can manually select it with `--edit-format udiff`.

- udiff_coder.py
- udiff_prompts.py

When experimenting with coder backends, it helps to run aider with `--verbose --no-pretty` so you can see
all the raw information being sent to/from the LLM in the conversation.

You can also refer to the
[instructions for installing a development version of aider](https://aider.chat/docs/install/optional.html#install-the-development-version-of-aider).


