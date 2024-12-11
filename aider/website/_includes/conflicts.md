
## Avoid package conflicts

You can avoid python package conflicts by installing aider using 
[pipx](/docs/install/pipx.html)
or
[uv](/docs/install/uv.html).

If you are using aider to work on a python project, sometimes your project will require
specific versions of python packages which conflict with the versions that aider
requires.
If this happens, the `python -m pip install aide-chat` command may return errors like these:

```
aider-chat 0.23.0 requires somepackage==X.Y.Z, but you have somepackage U.W.V which is incompatible.
```

which will install it globally on your system
within its own python environment.
This way you can use aider to work on any python project,
even if that project has conflicting dependencies.
