---
parent: Installation
nav_order: 20
---

# Optional steps
{: .no_toc }

The steps below are completely optional.

- TOC
{:toc}

## Install git

Aider works best if you have git installed.
Here are
[instructions for installing git in various environments](https://github.com/git-guides/install-git).

## Get your API key

To work with OpenAI's models like GPT-4o or o1-preview you need a paid
[OpenAI API key](https://help.openai.com/en/articles/4936850-where-do-i-find-my-secret-api-key).
Note that this is different than being a "ChatGPT Plus" subscriber.

To work with Anthropic's models like Claude 3.5 Sonnet you need a paid
[Anthropic API key](https://docs.anthropic.com/claude/reference/getting-started-with-the-api).


### Working with other LLMs

{% include works-best.md %}

### Store your api keys 

You can [store your api keys in configuration or env files](/docs/config/api-keys.html)
and they will be loaded automatically whenever you run aider.

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


## Enable voice coding 

Aider supports 
[coding with your voice](https://aider.chat/docs/usage/voice.html)
using the in-chat `/voice` command.
Aider uses the [PortAudio](http://www.portaudio.com) library to
capture audio.
Installing PortAudio is completely optional, but can usually be accomplished like this:

- For Windows, there is no need to install PortAudio.
- For Mac, do `brew install portaudio`
- For Linux, do `sudo apt-get install libportaudio2`
  - Some linux environments may also need `sudo apt install libasound2-plugins`

## Add aider to your editor 

Other projects have integrated aider into some IDE/editors.
It's not clear if they are tracking the latest
versions of aider,
so it may be best to just run the latest
aider in a terminal alongside your editor.

### NeoVim

[joshuavial](https://github.com/joshuavial) provided a NeoVim plugin for aider:

[https://github.com/joshuavial/aider.nvim](https://github.com/joshuavial/aider.nvim)

### VS Code

joshuavial also confirmed that aider works inside a VS Code terminal window.
Aider detects if it is running inside VSCode and turns off pretty/color output,
since the VSCode terminal doesn't seem to support it well.

### Other editors

If you are interested in creating an aider plugin for your favorite editor,
please let me know by opening a
[GitHub issue](https://github.com/Aider-AI/aider/issues).


## Install the development version of aider 

If you want the very latest development version of aider
you can install directly from GitHub:

```
aider --install-main-branch
```
