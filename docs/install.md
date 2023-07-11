
# Installing aider

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

Finally, you can also just provide your key as a command line argument:

```
aider --openai-api-key sk-...
```

## Install git

Make sure you have git installed and available on your shell path.
Here are
[instructions for installing git in various environments](https://github.com/git-guides/install-git).

## You are done!

The rest of these install steps are completely options.

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

* Mac: `brew install universal-ctags`
* Windows: `choco install universal-ctags`
* Ubuntu: `sudo apt-get install universal-ctags`

Some things to be aware of:

* The `ctags` command needs to be on your shell path so that it will run by default when aider invokes `ctags ...`.
* You need a build which includes the json feature. You can check by running `ctags --version` and looking for `+json` in the `Optional compiled features` list.


## Add aider to your editor (optional)

[joshuavial](https://github.com/joshuavial) has provided a NeoVim plugin for aider:

* [https://github.com/joshuavial/aider.nvim](https://github.com/joshuavial/aider.nvim)

If you are interested in creating an aider plugin for your favorite editor,
please let me know by opening a
[GitHub issue](https://github.com/paul-gauthier/aider/issues).
