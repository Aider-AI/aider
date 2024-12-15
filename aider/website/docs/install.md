---
title: Installation
has_children: true
nav_order: 20
description: How to install and get started pair programming with aider.
---

# Installation
{: .no_toc }


## Get started quickly with aider-install

{% include get-started.md %}

If needed, 
aider-install will automatically install a separate version of python3.12 to use with aider.

There are some [optional install steps](/docs/install/optional.html) you could consider.
See the [usage instructions](https://aider.chat/docs/usage.html) to start coding with aider.

## Install with uv

A recommended way to install aider is with uv:

```bash
python -m pip install uv  # If you need to install uv
uv tool install --python python3.12 aider-chat
```

You can use uv to install aider with your existing python versions 3.8-3.13.
If needed, 
uv will automatically install a separate version of python3.12 to use with aider.

Also see the
[docs on other methods for installing uv itself](https://docs.astral.sh/uv/getting-started/installation/).

## Install with pipx

A recommended way to install aider is with pipx:

```bash
python -m pip install pipx  # If you need to install pipx
pipx install aider-chat
```

You can use pipx to install aider with python versions 3.9-3.12.

Also see the
[docs on other methods for installing pipx itself](https://pipx.pypa.io/stable/installation/).


## Install with pip

You can directly install aider with pip, but one of the above
methods is usually safer.
If you do install with pip, you should consider
using a 
[virtual environment](https://docs.python.org/3/library/venv.html)
to keep aider's dependencies separated.


You can use pip to install aider with python versions 3.9-3.12.

```bash
# Install aider
python -m pip install -U --upgrade-strategy only-if-needed aider-chat

# To work with GPT-4o:
aider --4o --openai-api-key sk-xxx...

# To work with Claude 3.5 Sonnet:
aider --sonnet --anthropic-api-key sk-xxx...
```

{% include python-m-aider.md %}

## Installing with package managers

It's best to install aider using aider-install, uv or pipx as described above.
While aider is available in a number of system package managers,
they often install aider with incorrect dependencies.

## Next steps...

There are some [optional install steps](/docs/install/optional.html) you could consider.
See the [usage instructions](https://aider.chat/docs/usage.html) to start coding with aider.

