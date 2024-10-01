---
parent: More info
nav_order: 960
description: Aider uses various "edit formats" to let LLMs edit source files.
---

# Edit formats

Aider uses various "edit formats" to let LLMs edit source files.
Different models work better or worse with different edit formats.
Aider is configured to use the optimal format for most popular, common models.
You can always force use of a specific edit format with 
the `--edit-format` switch.

## whole

The "whole" edit format is the simplest possible editing format.
The LLM is instructed to return a full, updated
copy of each source file that needs changes.
While simple, it can be slow and costly because the LLM has to return
the *entire file* even if just a few lines are edited.

The format expects the file path just before the fenced file content:

````
show_greeting.py
```
import sys

def greeting(name):
    print(f"Hey {{name}}")

if __name__ == '__main__':
    greeting(sys.argv[1])
```
````


## diff

The "diff" edit format asks the LLM to specify file edits as a series of search/replace blocks.
This is an efficient format, because the model only needs to return parts of the file
which have changes.

They are formatted using a syntax similar to the git merge conflict resolution markings,
with the file path right before a fenced block:

````
mathweb/flask/app.py
```
<<<<<<< SEARCH
from flask import Flask
=======
import math
from flask import Flask
>>>>>>> REPLACE
```
````

## diff-fenced

The "diff-fenced" edit format is based on the diff format, but
the file path is placed inside the fence.
It is primarily used with the Gemini family of models,
which often fail to conform to fencing approach specified in the diff format.

````
```
mathweb/flask/app.py
<<<<<<< SEARCH
from flask import Flask
=======
import math
from flask import Flask
>>>>>>> REPLACE
```
````

## udiff

The "udiff" edit format is based on the widely used unified diff format,
but [modified and simplified](/2023/12/21/unified-diffs.html).
This is an efficient format, because the model only needs to return parts of the file
which have changes.

It was mainly used to the GPT-4 Turbo family of models,
to reduce their "lazy coding" tendencies with other edit formats.


````
```diff
--- mathweb/flask/app.py
+++ mathweb/flask/app.py
@@ ... @@
-class MathWeb:
+import sympy
+
+class MathWeb:
```
````

## editor-diff and editor-whole

These are streamlined versions of the diff and whole formats, intended to be used
with `--editor-edit-format` when using
[architect mode](/docs/usage/modes.html).
