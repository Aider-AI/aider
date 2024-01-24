
# Installing aider

- [Install git](#install-git)
- [Get your OpenAI API key](#get-your-openai-api-key)
- [Windows install](#windows-install)
- [MacOS or Linux install](#macos-or-linux-install)

## Install git

Make sure you have git installed.
Here are
[instructions for installing git in various environments](https://github.com/git-guides/install-git).

## Get your OpenAI API key

You need a paid
[OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key).
Note that this is different than being a "ChatGPT Plus" subscriber.

## Windows install

```
# Install aider
py -m pip install aider-chat

# Launch aider
aider --openai-api-key sk-xxxxxxxxxxxxxxx
```

## MacOS or Linux install


```
# Install aider
python -m pip install aider-chat

# Launch aider
aider --openai-api-key sk-xxxxxxxxxxxxxxx
```

## You are done!

See the [usage instructions](/#usage) to start coding with aider.

---

# Optional steps

The steps below are completely optional.

- [Store your API key (optional)](#store-your-api-key-optional)
- [Add aider to your editor (optional)](#add-aider-to-your-editor-optional)
- [Install PortAudio (optional)](#install-portaudio-optional)

## Store your api key (optional)

You can place your api key in an environment variable:

* `export OPENAI_API_KEY=sk-...` on Linux or Mac
* `setx OPENAI_API_KEY sk-...` in Windows PowerShell

Or you can create a `.aider.conf.yml` file in your home directory.
Put a line in it like this to specify your api key:

```
openai-api-key: sk-...
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

### NeoVim

[joshuavial](https://github.com/joshuavial) provided a NeoVim plugin for aider:

[https://github.com/joshuavial/aider.nvim](https://github.com/joshuavial/aider.nvim)

### VS Code

joshuavial also confirmed that aider works inside a VS Code terminal window.
Aider detects if it is running inside VSCode and turns off pretty/color output,
since the VSCode terminal doesn't seem to support it well.

[MattFlower](https://github.com/MattFlower) provided a VSCode plugin for aider:

[https://marketplace.visualstudio.com/items?itemName=MattFlower.aider](https://marketplace.visualstudio.com/items?itemName=MattFlower.aider)

### Other editors

If you are interested in creating an aider plugin for your favorite editor,
please let me know by opening a
[GitHub issue](https://github.com/paul-gauthier/aider/issues).


## Install development versions of aider (optional)

If you want to install the very latest development version of aider:

* GitHub hosts the latest version, which is under active development:
  * `python -m pip install git+https://github.com/paul-gauthier/aider.git`
* If you've git cloned the aider repository already, you can install "live" from your local copy. This is mostly useful if you are developing aider and want your current modifications to take effect immediately.
  * `python -m pip install -e .`

