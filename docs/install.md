
# Installing aider

- [pip install aider-chat](#pip-install-aider-chat)
- [Provide your OpenAI API key](#provide-your-openai-api-key)
- [Install git](#install-git)

Optional steps:

- [Install universal ctags (optional)](#install-universal-ctags-optional)
- [Add aider to your editor (optional)](#add-aider-to-your-editor-optional)
- [Install PortAudio (optional)](#install-portaudio-optional)

## pip install aider-chat

Install the “aider-chat” package with pip from one of these sources:

* PyPI hosts the released and most stable version:
  * `python -m pip install aider-chat`
* GitHub hosts the latest version, which is under active development:
  * `python -m pip install git+https://github.com/paul-gauthier/aider.git`
* If you've git cloned the aider repository already, you can install "live" from your local copy. This is mostly useful if you are developing aider and want your current modifications to take effect immediately.
  * `python -m pip install -e .`

On Windows, you may need to run `py -m pip install ...` to install python packages.

## Provide your OpenAI API key

You need a
[paid API key from OpenAI](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key)
to use aider. Note that this is different than being a "ChatGPT Plus" subscriber.

You can place your api key in an environment variable:

* `export OPENAI_API_KEY=sk-...` on Linux or Mac
* `setx OPENAI_API_KEY sk-...` in Windows PowerShell

Or you can create a `.aider.conf.yml` file in your home directory.
Put a line in it like this to specify your api key:

```
openai-api-key: sk-...
```

Or you can provide your key as a command line argument:

```
aider --openai-api-key sk-...
```

## Install git

Make sure you have git installed and available on your shell path.
Here are
[instructions for installing git in various environments](https://github.com/git-guides/install-git).

## You are done!

See the [usage instructions](/#usage) to start coding with aider.

The rest of the install steps are completely optional.

---


## Install universal ctags (optional)

Aider does not require ctags, and will operate just fine without it.

Installing ctags is helpful if you plan to use aider and GPT-4 with repositories
that have more than a handful of files.
This allows aider to build a
[map of your entire git repo](https://aider.chat/docs/ctags.html)
and share it with GPT to help it better understand and modify large codebases.

Aider only attempts to use ctags with GPT-4,
and currently doesn't use ctags at all with GPT-3.5.
So if your OpenAI API key doesn't support GPT-4, then you don't need ctags.

You should consult the
[universal ctags repo](https://github.com/universal-ctags/ctags)
for official instructions on how to install it in your environment.
But you may be able to install a compatible version using these commands:

* Mac: `brew update && brew install universal-ctags`
* Windows: `choco install universal-ctags`
* Ubuntu: `sudo apt update && sudo apt install universal-ctags`

You know aider has found a working ctags if you see this output when you launch aider:

```
Aider v0.8.3-dev
Model: gpt-4
Git repo: .git
Repo-map: universal-ctags using 1024 tokens <======
```

Some things to be aware of:

* The `ctags` command needs to be on your shell path so that it will run by default when aider invokes `ctags ...`.
* You need a build which includes the json feature. You can check by running `ctags --version` and looking for `+json` in the `Optional compiled features` list.

```
$ ctags --version

Universal Ctags 6.0.0, Copyright (C) 2015-2022 Universal Ctags Team
Universal Ctags is derived from Exuberant Ctags.
Exuberant Ctags 5.8, Copyright (C) 1996-2009 Darren Hiebert
  Compiled: Jun 25 2023, 07:31:18
  URL: https://ctags.io/
  Output version: 0.0
  Optional compiled features: +wildcards, +regex, +gnulib_fnmatch, +gnulib_regex, +iconv, +option-directory, +xpath, +json, +interactive, +yaml, +case-insensitive-filenames, +packcc, +optscript, +pcre2
```

## Install PortAudio (optional)

Aider supports [coding with your voice](https://aider.chat/docs/voice.html)
using the in-chat `/voice` command.
Aider uses the [PortAudio](http://www.portaudio.com) library to
capture audio.
Installing PortAudio is completely optional, but can usually be accomplished like this:

- For Windows, there is no need to install PortAudio.
- For Mac, do `brew install portaudio`
- For Linux, do `sudo apt-get install libportaudio2`

## Add aider to your editor (optional)

[joshuavial](https://github.com/joshuavial) has been working on editor integrations.

### NeoVim

He provided a NeoVim plugin for aider:

[https://github.com/joshuavial/aider.nvim](https://github.com/joshuavial/aider.nvim)

### VS Code

He also confirmed that aider works inside a VS Code terminal window, but
found that you should
[run with `--no-pretty` to avoid flickering issues](https://github.com/paul-gauthier/aider/issues/68#issuecomment-1634985231).

### Other editors

If you are interested in creating an aider plugin for your favorite editor,
please let me know by opening a
[GitHub issue](https://github.com/paul-gauthier/aider/issues).
