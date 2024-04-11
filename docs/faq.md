
# Frequently asked questions

- [How does aider use git?](#how-does-aider-use-git)
- [GPT-4 vs GPT-3.5](#gpt-4-vs-gpt-35)
- [Can I use aider with other LLMs, local LLMs, etc?](#can-i-use-aider-with-other-llms-local-llms-etc)
- [Accessing other LLMs with OpenRouter](#accessing-other-llms-with-openrouter)
- [Aider isn't editing my files?](#aider-isnt-editing-my-files)
- [Can I run aider in Google Colab?](#can-i-run-aider-in-google-colab)
- [How can I run aider locally from source code?](#how-can-i-run-aider-locally-from-source-code)
- [Can I script aider?](#can-i-script-aider)
- [What code languages does aider support?](#what-code-languages-does-aider-support)
- [How to use pipx to avoid python package conflicts?](#how-to-use-pipx-to-avoid-python-package-conflicts)
- [How can I add ALL the files to the chat?](#how-can-i-add-all-the-files-to-the-chat)
- [Can I specify guidelines or conventions?](#can-i-specify-guidelines-or-conventions)
- [Can I change the system prompts that aider uses?](#can-i-change-the-system-prompts-that-aider-uses)

## How does aider use git?

Aider works best with code that is part of a git repo.
Aider is tightly integrated with git, which makes it easy to:

  - Use git to undo any GPT changes that you don't like
  - Go back in the git history to review the changes GPT made to your code
  - Manage a series of GPT's changes on a git branch

Aider specifically uses git in these ways:

  - It asks to create a git repo if you launch it in a directory without one.
  - Whenever GPT edits a file, aider commits those changes with a descriptive commit message. This makes it easy to undo or review GPT's changes.
  - Aider takes special care if GPT tries to edit files that already have uncommitted changes (dirty files). Aider will first commit any preexisting changes with a descriptive commit message. This keeps your edits separate from GPT's edits, and makes sure you never lose your work if GPT makes an inappropriate change.

Aider also allows you to use in-chat commands to `/diff` or `/undo` the last change made by GPT.
To do more complex management of your git history, you cat use raw `git` commands,
either by using `/git` within the chat, or with standard git tools outside of aider.

While it is not recommended, you can disable aider's use of git in a few ways:

  - `--no-auto-commits` will stop aider from git committing each of GPT's changes.
  - `--no-dirty-commits` will stop aider from committing dirty files before applying GPT's edits.
  - `--no-git` will completely stop aider from using git on your files. You should ensure you are keeping sensible backups of the files you are working with.

## GPT-4 vs GPT-3.5

Aider supports all of OpenAI's chat models,
and uses GPT-4 Turbo by default.
It has a large context window, good coding skills and
generally obeys the instructions in the system prompt.

You can choose another model with the `--model` command line argument
or one of these shortcuts:

```
aider -4 # to use gpt-4-0613
aider -3 # to use gpt-3.5-turbo-0125
```

The older `gpt-4-0613` model is a great choice if GPT-4 Turbo is having
trouble with your coding task, although it has a smaller context window
which can be a real limitation.

All the GPT-4 models are able to structure code edits as "diffs"
and use a
[repository map](https://aider.chat/docs/repomap.html)
to improve its ability to make changes in larger codebases.

GPT-3.5 is
limited to editing somewhat smaller codebases.
It is less able to follow instructions and
so can't reliably return code edits as "diffs".
Aider disables the
repository map
when using GPT-3.5.

For detailed quantitative comparisons of the various models, please see the
[aider blog](https://aider.chat/blog/)
which contains many benchmarking articles.

## Can I use aider with other LLMs, local LLMs, etc?

Aider provides experimental support for LLMs other than OpenAI's GPT-3.5 and GPT-4. The support is currently only experimental for two reasons:

- GPT-3.5 is just barely capable of *editing code* to provide aider's interactive "pair programming" style workflow. None of the other models seem to be as capable as GPT-3.5 yet.
- Just "hooking up" aider to a new model by connecting to its API is almost certainly not enough to get it working in a useful way. Getting aider working well with GPT-3.5 and GPT-4 was a significant undertaking, involving [specific code editing prompts and backends for each model and extensive benchmarking](https://aider.chat/docs/benchmarks.html). Officially supporting each new LLM will probably require a similar effort to tailor the prompts and editing backends.

Numerous users have done experiments with numerous models. None of these experiments have yet identified other models that look like they are capable of working well with aider.

Once we see signs that a *particular* model is capable of code editing, it would be reasonable for aider to attempt to officially support such a model. Until then, aider will simply maintain experimental support for using alternative models.

There are ongoing discussions about [LLM integrations in the aider discord](https://discord.gg/yaUk7JqJ9G).

Here are some [GitHub issues which may contain relevant information](https://github.com/paul-gauthier/aider/issues?q=is%3Aissue+%23172).

### OpenAI API compatible LLMs

If you can make the model accessible via an OpenAI compatible API,
you can use `--openai-api-base` to connect to a different API endpoint.

### Local LLMs

[LiteLLM](https://github.com/BerriAI/litellm) and
[LocalAI](https://github.com/go-skynet/LocalAI)
are relevant tools to serve local models via an OpenAI compatible API.


### Azure

Aider can be configured to connect to the OpenAI models on Azure.
Aider supports the configuration changes specified in the
[official openai python library docs](https://github.com/openai/openai-python#microsoft-azure-endpoints).
You should be able to run aider with the following arguments to connect to Azure:

```
$ aider \
    --openai-api-type azure \
    --openai-api-key your-key-goes-here \
    --openai-api-base https://example-endpoint.openai.azure.com \
    --openai-api-version 2023-05-15 \
    --openai-api-deployment-id deployment-name \
    ...
```

You could also store those values in an `.aider.conf.yml` file in your home directory:

```
openai-api-type: azure
openai-api-key: your-key-goes-here
openai-api-base: https://example-endpoint.openai.azure.com
openai-api-version: 2023-05-15
openai-api-deployment-id: deployment-name
```

See the
[official Azure documentation on using OpenAI models](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/chatgpt-quickstart?tabs=command-line&pivots=programming-language-python)
for more information on how to populate the above configuration values.


## Accessing other LLMs with OpenRouter

[OpenRouter](https://openrouter.ai) provide an interface to [many models](https://openrouter.ai/models) which are not widely accessible, in particular Claude 3 Opus.

To access the OpenRouter models, simply:

```
# Install aider
pip install aider-chat

# Setup OpenRouter access
export OPENAI_API_KEY=<your-openrouter-key>
export OPENAI_API_BASE=https://openrouter.ai/api/v1

# For example, run aider with Claude 3 Opus using the diff editing format
aider --model anthropic/claude-3-opus --edit-format diff
```


## Aider isn't editing my files?

Sometimes GPT will reply with some code changes that don't get applied to your local files.
In these cases, aider might say something like "Failed to apply edit to *filename*".

This usually happens because GPT is not specifying the edits
to make in the format that aider expects.
GPT-3.5 is especially prone to disobeying the system prompt instructions in this manner, but it also happens with GPT-4.

Aider makes every effort to get GPT to conform, and works hard to deal with
replies that are "almost" correctly formatted.
If Aider detects an improperly formatted reply, it gives GPT feedback to try again.
Also, before each release new versions of aider are
[benchmarked](https://aider.chat/docs/benchmarks.html).
This helps prevent regressions in the code editing
performance of GPT that could have been inadvertantly
introduced.

But sometimes GPT just won't cooperate.
In these cases, here are some things you might try:

  - Try the older GPT-4 model `gpt-4-0613` not GPT-4 Turbo by running `aider --model gpt-4-0613`.
  - Use `/drop` to remove files from the chat session which aren't needed for the task at hand. This will reduce distractions and may help GPT produce properly formatted edits.
  - Use `/clear` to remove the conversation history, again to help GPT focus.


## Can I run aider in Google Colab?

User [imabutahersiddik](https://github.com/imabutahersiddik)
has provided this
[Colab notebook](https://colab.research.google.com/drive/1J9XynhrCqekPL5PR6olHP6eE--rnnjS9?usp=sharing).

## How can I run aider locally from source code?

To run the project locally, follow these steps:

```
# Clone the repository:
git clone git@github.com:paul-gauthier/aider.git

# Navigate to the project directory:
cd aider

# Install the dependencies listed in the `requirements.txt` file:
pip install -r requirements.txt

# Run the local version of Aider:
python -m aider.main
```

# Can I script aider?

You can script aider via the command line or python.

## Command line

Aider takes a `--message` argument, where you can give it a natural language instruction.
It will do that one thing, apply the edits to the files and then exit.
So you could do:

```bash
aider --message "make a script that prints hello" hello.js
```

Or you can write simple shell scripts to apply the same instruction to many files:

```bash
for FILE in *.py ; do
    aider --message "add descriptive docstrings to all the functions" $FILE
done
```

User `aider --help` to see all the command line options, but these are useful for scripting:

```
--stream, --no-stream
                      Enable/disable streaming responses (default: True) [env var:
                      AIDER_STREAM]
--message COMMAND, --msg COMMAND, -m COMMAND
                      Specify a single message to send GPT, process reply then exit
                      (disables chat mode) [env var: AIDER_MESSAGE]
--message-file MESSAGE_FILE, -f MESSAGE_FILE
                      Specify a file containing the message to send GPT, process reply,
                      then exit (disables chat mode) [env var: AIDER_MESSAGE_FILE]
--yes                 Always say yes to every confirmation [env var: AIDER_YES]
--auto-commits, --no-auto-commits
                      Enable/disable auto commit of GPT changes (default: True) [env var:
                      AIDER_AUTO_COMMITS]
--dirty-commits, --no-dirty-commits
                      Enable/disable commits when repo is found dirty (default: True) [env
                      var: AIDER_DIRTY_COMMITS]
--dry-run, --no-dry-run
                      Perform a dry run without modifying files (default: False) [env var:
                      AIDER_DRY_RUN]
--commit              Commit all pending changes with a suitable commit message, then exit
                      [env var: AIDER_COMMIT]
```


## Python

You can also script aider from python:

```python
import os
import openai
from aider.coders import Coder

# Make an openai client
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# This is a list of files to add to the chat
fnames = ["foo.py"]

# Create a coder object
coder = Coder.create(client=client, fnames=fnames)

# This will execute one instruction on those files and then return
coder.run("make a script that prints hello world")

# Send another instruction
coder.run("make it say goodbye")
```

See the
[Coder.create() and Coder.__init__() methods](https://github.com/paul-gauthier/aider/blob/main/aider/coders/base_coder.py)
for all the supported arguments.

It can also helpful to set the equivalend of `--yes` by doing this:

```
from aider.io import InputOutput
io = InputOutput(yes=True)
# ...
coder = Coder.create(client=client, fnames=fnames, io=io)
```

## What code languages does aider support?

Aider supports pretty much all the popular coding languages.
This is partly because GPT-4 is fluent in most mainstream languages,
and familiar with popular libraries, packages and frameworks.

In fact, coding with aider is sometimes the most magical
when you're working in a language that you
are less familiar with.
GPT often knows the language better than you,
and can generate all the boilerplate to get to the heart of your
problem.
GPT will often solve your problem in an elegant way
using a library or package that you weren't even aware of.

Aider uses tree-sitter to do code analysis and help
GPT navigate larger code bases by producing
a [repository map](https://aider.chat/docs/repomap.html).

Aider can currently produce repository maps for most mainstream languages, listed below.
But aider should work quite well for other languages, even without repo map support.

- C
- C#
- C++
- Emacs Lisp
- Elixir
- Elm
- Go
- Java
- Javascript
- OCaml
- PHP
- Python
- QL
- Ruby
- Rust
- Typescript

## How to use pipx to avoid python package conflicts?

If you are using aider to work on a python project, sometimes your project will require
specific versions of python packages which conflict with the versions that aider
requires.
If this happens, the `pip install` command may return errors like these:

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

## How can I add ALL the files to the chat?

People regularly ask about how to add **many or all of their repo's files** to the chat.
This is probably not a good idea and will likely do more harm than good.

The best approach is think about which files need to be changed to accomplish
the task you are working on. Just add those files to the chat.

Usually when people want to add "all the files" it's because they think it
will give GPT helpful context about the overall code base.
Aider will automatically give GPT a bunch of additional context about
how those specific files relate to
the rest of your git repo.
It does this by analyzing your entire codebase in light of the
current chat to build a compact
[repository map](https://aider.chat/2023/10/22/repomap.html).

Adding a bunch of files that are mostly irrelevant to the
task at hand will often distract or confuse GPT.
GPT will give worse coding results, and sometimese even fail to correctly edit files.
Addings extra files will also increase the token costs on your OpenAI invoice.

Again, it's usually best to just add the files to the chat that will need to be modified.
If you still wish to add lots of files to the chat, you can:

- Use a wildcard when you launch aider: `aider src/*.py`
- Use a wildcard with the in chat `/add` command: `/add src/*.py`
- Give the `/add` command a directory name and it will recurisvely add every file under that dir: `/add src`

## Can I specify guidelines or conventions?

Sometimes you want GPT to be aware of certain coding guidelines,
like whether to provide type hints, which libraries or packages
to prefer, etc.

Just put any extra instructions in a file
like `CONVENTIONS.md` and then add it to the chat.

For more details, see this documentation on
[using a conventions file with aider](https://aider.chat/docs/conventions.html).

## Can I change the system prompts that aider uses?

Aider is set up to support different system prompts and edit formats
in a modular way. If you look in the `aider/coders` subdirectory, you'll
see there's a base coder with base prompts, and then there are
a number of
different specific coder implementations.

If you're thinking about experimenting with system prompts
this document about
[benchmarking GPT-3.5 and GPT-4 on code editing](https://aider.chat/docs/benchmarks.html)
might be useful background.

While it's not well documented how to add new coder subsystems, you may be able
to modify an existing implementation or use it as a template to add another.

To get started, try looking at and modifying these files.

The wholefile coder is currently used by GPT-3.5 by default. You can manually select it with `--edit-format whole`.

- wholefile_coder.py
- wholefile_prompts.py

The editblock coder is currently used by GPT-4 by default. You can manually select it with `--edit-format diff`.

- editblock_coder.py
- editblock_prompts.py

The universal diff coder is currently used by GPT-4 Turbo by default. You can manually select it with `--edit-format udiff`.

- udiff_coder.py
- udiff_prompts.py

When experimenting with coder backends, it helps to run aider with `--verbose --no-pretty` so you can see
all the raw information being sent to/from GPT in the conversation.

You can also refer to the
[instructions for installing a development version of aider](https://aider.chat/docs/install.html#install-development-versions-of-aider-optional).