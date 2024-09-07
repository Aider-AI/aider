---
parent: Installation
nav_order: 100
---

# Install with pipx

If you are using aider to work on a python project, sometimes your project will require
specific versions of python packages which conflict with the versions that aider
requires.
If this happens, the `python -m pip install` command may return errors like these:

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


## pipx on replit

To use aider with pipx on replit, you can run these commands in the replit shell:

```
pip install pipx
pipx run aider-chat ...normal aider args...
```

If you install aider with pipx on replit and try and run it as just `aider` it will crash with a missing `libstdc++.so.6` library.

