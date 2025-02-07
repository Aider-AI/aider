---
title: Using uv as an installer
excerpt: Reliably packaging & distributing python CLI tools is hard. Aider uses uv in novel ways to make it easy to install the aider CLI, its dependencies and python 3.12. All in an isolated env.
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Using uv as an installer
{: .no_toc }

It's hard to reliably
package and distribute python command line tools
to end users.
Users frequently encounter challenges:
dependency version conflicts, virtual environment management,
needing to install python or a specific version of python, etc.

Aider employs [uv](https://github.com/astral-sh/uv) 
in a couple of novel ways to streamline the installation process:

1. Install aider with
`curl https://aider.chat/install.sh | sh` even if python isn't already installed.

2. Users who have python 3.8+ installed can `pip install aider-install && aider-install`.

Both methods use uv to **globally** install the `aider` command line program,
with all of its dependencies in an **isolated environment**.
They ensure that aider will run with **python 3.12**, and install that version
if it is not already available.

These uv install methods are especially helpful for aider, because it 
has a large set of very specific dependencies.
Since not all of aider's dependencies are available on all python versions,
it requires python 3.9-3.12.

Most users don't want to worry about these details --
they just want a quick way to install and run aider.


## One-liners

Users can install aider with a shell one-liner, without even having python previously installed:

```bash
curl -LsSf https://aider.chat/install.sh | sh
```

This installs uv, then uses it to install python 3.12, 
install the `aider` command line tool
and update the user's shell path.
Under the hood, it is simply a copy of 
uv's own install script `https://astral.sh/uv/install.sh`
with [one line added](https://github.com/Aider-AI/aider/blob/4251e976b3aa52c2a3af08da4b203d4d524c8e92/aider/website/install.sh#L1181), to install aider as a tool:

```
ensure "${_install_dir}/uv" tool install --force --python python3.12 aider-chat@latest
```


## aider-install

The aider-install python package allows quick global installation of aider
for users who already have python 3.8+ installed.
It simply provides the `aider-install` command line program,
which users just need to run once.

```bash
pip install aider-install
aider-install
```

The `pip install aider-install` installs only two packages: 
aider-install and the [uv python package](https://pypi.org/project/uv/).
This ensures that uv is available
in the user's environment.
Everything else is installed in a stand-alone environment created by uv.

When the user runs `aider-install`, it runs uv
to install aider as a tool and update the user's shell path if needed:

```bash
uv tool install --force --python python3.12 aider-chat
uv tool update-shell
```


## Benefits

These uv install methods have been popular with users,
providing a hassle free way to install aider and quickly get started.
Installs are also extremely fast, much faster than pip or pipx installs
even when uv is also installing python 3.12!

There are also a number of benefits from the perspective of the tool developer/publisher.
Since providing these install methods, far fewer users report dependency problems and 
version conflicts as compared to users who `pip install aider-chat`.
There is also less pressure to rapidly support the newest python versions, 
since aider always installs with python 3.12.

