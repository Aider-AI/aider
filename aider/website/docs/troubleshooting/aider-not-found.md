---
parent: Troubleshooting
nav_order: 28
---

# Aider not found

In some environments the `aider` command may not be available
on your shell path.
This can occur because of permissions/security settings in your OS,
and often happens to Windows users.

You may see an error message like this:

> aider: The term 'aider' is not recognized as a name of a cmdlet, function, script file, or executable program. Check the spelling of the name, or if a path was included, verify that the path is correct and try again.

Below is the most fail safe way to install and run aider in these situations:

```
python -m pip install aider-chat
python -m aider
```


{% include venv-pipx.md %}
