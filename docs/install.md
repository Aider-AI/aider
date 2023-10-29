
# Installing aider

- [pip install aider-chat](#pip-install-aider-chat)
- [Provide your OpenAI API key](#provide-your-openai-api-key)
- [Install git](#install-git)

Optional steps:

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
