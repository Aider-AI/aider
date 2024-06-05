---
nav_order: 30
---

## Usage

Run `aider` with the source code files you want to edit.
These files will be "added to the chat session", so that the LLM can see their
contents and edit them according to your instructions.

```
aider <file1> <file2> ...
```

Be selective, and just add the files that the LLM will need to edit.
If you add a bunch of unrelated files, the LLM can get overwhelmed
and confused (and it costs more tokens).
Aider will automatically
share snippets from other, related files with the LLM so it can
[understand the rest of your code base](https://aider.chat/docs/repomap.html).

You can also just launch aider anywhere in a git repo without naming
files on the command line.  It will discover all the files in the
repo.  You can then add and remove individual files in the chat
session with the `/add` and `/drop` chat commands described below.
If you or the LLM mention any of the repo's filenames in the conversation,
aider will ask if you'd like to add them to the chat.

Aider also has many other options which can be set with
command line switches, environment variables or via a configuration file.
See `aider --help` for details.
