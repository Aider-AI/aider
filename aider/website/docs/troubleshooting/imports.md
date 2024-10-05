---
parent: Troubleshooting
nav_order: 28
---

# Dependency versions

Aider expects to be installed via `pip` or `pipx`, which will install
correct versions of all of its required dependencies.

If you've been linked to this doc from a GitHub issue, 
or if aider is reporting `ImportErrors`
it is likely that your
aider install is using incorrect dependencies.

## Install with pipx

If you are having dependency problems you should consider
[installing aider using pipx](/docs/install/pipx.html).
This will ensure that aider is installed in its own python environment,
with the correct set of dependencies.

Try re-installing cleanly:

```
pipx uninstall aider-chat
pipx install aider-chat
```

## Package managers like Homebrew, AUR, ports

Package managers often install aider with the wrong dependencies, leading
to import errors and other problems.

The recommended way to 
install aider is with 
[pip](/docs/install/install.html).
Be sure to use the `--upgrade-strategy only-if-needed` switch so that the correct
versions of dependencies will be installed.

```
python -m pip install -U --upgrade-strategy only-if-needed aider-chat
```

A very safe way is to
[install aider using pipx](/docs/install/pipx.html),
which will ensure it is installed in a stand alone virtual environment.

## Dependency versions matter

Aider pins its dependencies and is tested to work with those specific versions.
If you are installing aider with pip (rather than pipx),
you should be careful about upgrading or downgrading the python packages that
aider uses.

In particular, be careful with the packages with pinned versions 
noted at the end of
[aider's requirements.in file](https://github.com/Aider-AI/aider/blob/main/requirements/requirements.in).
These versions are pinned because aider is known not to work with the
latest versions of these libraries.

Also be wary of upgrading `litellm`, as it changes versions frequently
and sometimes introduces bugs or backwards incompatible changes.

## Replit

You can `pip install -U aider-chat` on replit.

Or you can install aider with
pipx as follows:

{% include replit-pipx.md %}
