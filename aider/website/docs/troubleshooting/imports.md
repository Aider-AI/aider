---
parent: Troubleshooting
nav_order: 28
---

# Import errors

Aider expects to be installed via `pip` or `pipx`, which will install
all of its required dependencies.
If aider reports `ImportErrors`, this probably means it has been installed
incorrectly.


## Dependency versions

Aider pins its dependencies and is tested to work with those specific versions.
You should be careful about upgrading or downgrading other python libraries that
aider uses.

If you need other versions of packages for your project,
consider
[installing aider using pipx](/docs/install/pipx.html).



## Replit

You can `pip install aider-chat` on replit, or you can install it via
pipx.

{% include replit-pipx.md %}
