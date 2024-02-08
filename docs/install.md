
# Installing aider

- [Install git](#install-git)
- [Get your OpenAI API key](#get-your-openai-api-key)
- [Windows install](#windows-install)
- [Mac/Linux install](#maclinux-install)
- [Tutorial videos](#tutorial-videos)

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

## Mac/Linux install


```
# Install aider
python -m pip install aider-chat

# Launch aider
aider --openai-api-key sk-xxxxxxxxxxxxxxx
```

## Tutorial videos

Here are a few tutorial videos:

- [Aider : the production ready AI coding assistant you've been waiting for](https://www.youtube.com/watch?v=zddJofosJuM) -- Learn Code With JV
- [Holy Grail: FREE Coding Assistant That Can Build From EXISTING CODE BASE](https://www.youtube.com/watch?v=df8afeb1FY8) -- Matthew Berman
- [Aider: This AI Coder Can Create AND Update Git Codebases](https://www.youtube.com/watch?v=EqLyFT78Sig) -- Ian Wootten

## You are done!

See the [usage instructions](/#usage) to start coding with aider.

---

# Optional steps

The steps below are completely optional.

- [Store your API key](#store-your-api-key-optional)
- [Enable Playwright](#enable-playwright) to enhance the `/web <url>` command.
- [Enable voice coding](#enable-voice-coding-optional)
- [Add aider to your editor](#add-aider-to-your-editor-optional)
- [Install development versions of aider](#install-development-versions-of-aider-optional)

## Store your api key (optional)

You can place your api key in an environment variable:

* `export OPENAI_API_KEY=sk-...` on Linux or Mac
* `setx OPENAI_API_KEY sk-...` in Windows PowerShell

Or you can create a `.aider.conf.yml` file in your home directory.
Put a line in it like this to specify your api key:

```
openai-api-key: sk-...
```

## Enable Playwright

Aider supports adding web pages to the chat with the `/web <url>` command.
When you add a url to the chat, aider fetches the page and scrapes its
content.

By default, aider uses the `httpx` library to scrape web pages, but this only
works on a subset of web pages.
Some sites explicitly block requests from tools like httpx.
Others rely heavily on javascript to render the page content,
which isn't possible using only httpx.

Aider works best with all web pages if you install
Playwright's chromium browser and its dependencies:

```
playwright install --with-deps chromium
```

See the
[Playwright for Python documentation](https://playwright.dev/python/docs/browsers#install-system-dependencies)
for additional information.


## Enable voice coding (optional)

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

