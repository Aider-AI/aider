---
nav_order: 60
---

# Frequently asked questions
{: .no_toc }

- TOC
{:toc}

## How does aider use git?

Aider works best with code that is part of a git repo.
Aider is tightly integrated with git, which makes it easy to:

  - Use git to undo any aider changes that you don't like
  - Go back in the git history to review the changes that aider made to your code
  - Manage a series of aider's changes on a git branch

Aider specifically uses git in these ways:

  - It asks to create a git repo if you launch it in a directory without one.
  - Whenever aider edits a file, it commits those changes with a descriptive commit message. This makes it easy to undo or review aider's changes.
  - Aider takes special care before editing files that already have uncommitted changes (dirty files). Aider will first commit any preexisting changes with a descriptive commit message. This keeps your edits separate from aider's edits, and makes sure you never lose your work if aider makes an inappropriate change.

Aider also allows you to use in-chat commands to `/diff` or `/undo` the last change.
To do more complex management of your git history, you cat use raw `git` commands,
either by using `/git` within the chat, or with standard git tools outside of aider.

While it is not recommended, you can disable aider's use of git in a few ways:

  - `--no-auto-commits` will stop aider from git committing each of its changes.
  - `--no-dirty-commits` will stop aider from committing dirty files before applying its edits.
  - `--no-git` will completely stop aider from using git on your files. You should ensure you are keeping sensible backups of the files you are working with.


## Can I run aider in Google Colab?

User [imabutahersiddik](https://github.com/imabutahersiddik)
has provided this
[Colab notebook](https://colab.research.google.com/drive/1J9XynhrCqekPL5PR6olHP6eE--rnnjS9?usp=sharing).

## How can I run aider locally from source code?

To run the project locally, follow these steps:

```
# Clone the repository:
git clone git@github.com:paul-gauthier/aider.git

# Navigate to the project directory:
cd aider

# Install the dependencies listed in the `requirements.txt` file:
pip install -r requirements.txt

# Run the local version of Aider:
python -m aider.main
```


## How to use pipx to avoid python package conflicts?

If you are using aider to work on a python project, sometimes your project will require
specific versions of python packages which conflict with the versions that aider
requires.
If this happens, the `pip install` command may return errors like these:

```
aider-chat 0.23.0 requires somepackage==X.Y.Z, but you have somepackage U.W.V which is incompatible.
```

You can avoid this problem by installing aider using `pipx`,
which will install it globally on your system
within its own python environment.
This way you can use aider to work on any python project,
even if that project has conflicting dependencies.

Install [pipx](https://pipx.pypa.io/stable/) then just do:

```
pipx install aider-chat
```

## Aider isn't editing my files?

Sometimes the LLM will reply with some code changes that don't get applied to your local files.
In these cases, aider might say something like "Failed to apply edit to *filename*".

This usually happens because the LLM is not specifying the edits
to make in the format that aider expects.
GPT-3.5 is especially prone to disobeying the system prompt instructions in this manner, but it also happens with stronger models.

Aider makes every effort to get the LLM
to conform, and works hard to deal with
replies that are "almost" correctly formatted.
If Aider detects an improperly formatted reply, it gives
the LLM feedback to try again.
Also, before each release new versions of aider are
[benchmarked](https://aider.chat/docs/benchmarks.html).
This helps prevent regressions in the code editing
performance of an LLM that could have been inadvertantly
introduced.

But sometimes the LLM just won't cooperate.
In these cases, here are some things you might try:

  - Use `/drop` to remove files from the chat session which aren't needed for the task at hand. This will reduce distractions and may help GPT produce properly formatted edits.
  - Use `/clear` to remove the conversation history, again to help GPT focus.
  - Try the a different LLM.

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
[instructions for installing a development version of aider](https://aider.chat/docs/install.html#install-development-versions-of-aider-optional).