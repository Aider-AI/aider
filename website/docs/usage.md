---
nav_order: 30
has_children: true
description: How to use aider to pair program with AI and edit code in your local git repo.
---

# Usage

Run `aider` with the source code files you want to edit.
These files will be "added to the chat session", so that
aider can see their
contents and edit them for you.
They can be existing files or the name of files you want
aider to create for you.

```
aider <file1> <file2> ...
```

At the aider `>` prompt, ask for code changes and aider
will edit those files to accomplish your request.


```
$ aider factorial.py

Aider v0.37.1-dev
Models: gpt-4o with diff edit format, weak model gpt-3.5-turbo
Git repo: .git with 258 files
Repo-map: using 1024 tokens
Use /help to see in-chat commands, run with --help to see cmd line args
───────────────────────────────────────────────────────────────────────
>`Make a program that asks for a number and prints its factorial

...
```

## Adding files

Just add the files that the aider will need to *edit*.
If you add too many files, the LLM can get overwhelmed
and confused (and it costs more tokens).
Aider will automatically
pull in content from related files so that it can
[understand the rest of your code base](https://aider.chat/docs/repomap.html).

You can also run aider without naming any files and use the in-chat
`/add` command to add files.

Or you can skip adding files completely, and aider
will try to figure out which files need to be edited based
on your requests.

## LLMs

Aider uses GPT-4o by default, but you can
[connect to many different LLMs](/docs/llms.html).
Claude 3 Opus is another model which works very well with aider,
which you can use by running `aider --opus`.

You can run `aider --model XXX` to launch aider with
a specific model.
Or, during your chat you can switch models with the in-chat
`/model` command.

## Making changes

Ask aider to make changes to your code.
It will show you some diffs of the changes it is making to
complete you request.
Aider will git commit all of its changes,
so they are easy to track and undo.

You can always use the `/undo` command to undo changes you don't
like.
