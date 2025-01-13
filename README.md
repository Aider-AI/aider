
<!-- Edit README.md, not index.md -->

# Aider REST API - AI Pair Programming as a Service

This fork of Aider focuses on providing a REST API interface to Aider's powerful AI pair programming capabilities. While maintaining all the original CLI features, it adds a robust API layer that allows you to integrate Aider's functionality into your own applications and services.

<p align="center">
  <a href="https://discord.gg/Tv2uQnR88V">
    <img src="https://img.shields.io/badge/Join-Discord-blue.svg"/>
  </a>
  <a href="https://aider.chat/docs/install.html">
    <img src="https://img.shields.io/badge/Read-Docs-green.svg"/>
  </a>
</p>

## REST API

Aider's REST API allows you to integrate AI pair programming capabilities into your applications. The API server can be started using:

```bash
python -m aider.server [aider_args]
```

For example, here's an advanced configuration using multiple models and features:
```bash
python -m aider.server --architect --model openrouter/anthropic/claude-3.5-sonnet:beta --editor-model openrouter/anthropic/claude-3.5-sonnet --weak-model claude-3-haiku-20240307 --cache-prompts --analytics
```

The server runs on `http://0.0.0.0:8000` by default and provides the following endpoints:

### POST /init
Initializes an Aider instance with the provided configuration.

Request body:
```json
{
    "pretty": false  // Optional, defaults to false
}
```

### POST /chat
Sends a message to chat with Aider.

Request body:
```json
{
    "content": "Your message here"
}
```

Response includes an array of responses with different types:
- tool_output: Results from tool operations
- error: Error messages
- warning: Warning messages
- print: General output messages
- system: System messages
- assistant: AI assistant responses

### POST /stop
Stops the Aider instance.

## CLI Usage
<!--[[[cog
# We can't "include" here.
# Because this page is rendered by GitHub as the repo README
cog.out(open("aider/website/_includes/get-started.md").read())
]]]-->

If you already have python 3.8-3.13 installed, you can get started quickly like this:

```bash
python -m pip install aider-install
aider-install

# Change directory into your code base
cd /to/your/project

# Work with Claude 3.5 Sonnet on your code
aider --model sonnet --anthropic-api-key your-key-goes-here

# Work with GPT-4o on your code
aider --model gpt-4o --openai-api-key your-key-goes-here
```
<!--[[[end]]]-->

See the
[installation instructions](https://aider.chat/docs/install.html)
and
[usage documentation](https://aider.chat/docs/usage.html)
for more details.

## Features

- Run aider with the files you want to edit: `aider <file1> <file2> ...`
- Ask for changes:
  - Add new features or test cases.
  - Describe a bug.
  - Paste in an error message or or GitHub issue URL.
  - Refactor code.
  - Update docs.
- Aider will edit your files to complete your request.
- Aider [automatically git commits](https://aider.chat/docs/git.html) changes with a sensible commit message.
- [Use aider inside your favorite editor or IDE](https://aider.chat/docs/usage/watch.html).
- Aider works with [most popular languages](https://aider.chat/docs/languages.html): python, javascript, typescript, php, html, css, and more...
- Aider can edit multiple files at once for complex requests.
- Aider uses a [map of your entire git repo](https://aider.chat/docs/repomap.html), which helps it work well in larger codebases.
- Edit files in your editor or IDE while chatting with aider,
and it will always use the latest version.
Pair program with AI.
- [Add images to the chat](https://aider.chat/docs/usage/images-urls.html) (GPT-4o, Claude 3.5 Sonnet, etc).
- [Add URLs to the chat](https://aider.chat/docs/usage/images-urls.html) and aider will read their content.
- [Code with your voice](https://aider.chat/docs/usage/voice.html).
- Aider works best with Claude 3.5 Sonnet, DeepSeek V3, o1 & GPT-4o and can [connect to almost any LLM](https://aider.chat/docs/llms.html).

## Top tier performance

[Aider has one of the top scores on SWE Bench](https://aider.chat/2024/06/02/main-swe-bench.html).
SWE Bench is a challenging software engineering benchmark where aider
solved *real* GitHub issues from popular open source
projects like django, scikitlearn, matplotlib, etc.

## More info

- [Documentation](https://aider.chat/)
- [Installation](https://aider.chat/docs/install.html)
- [Usage](https://aider.chat/docs/usage.html)
- [Tutorial videos](https://aider.chat/docs/usage/tutorials.html)
- [Connecting to LLMs](https://aider.chat/docs/llms.html)
- [Configuration](https://aider.chat/docs/config.html)
- [Troubleshooting](https://aider.chat/docs/troubleshooting.html)
- [LLM Leaderboards](https://aider.chat/docs/leaderboards/)
- [GitHub](https://github.com/Aider-AI/aider)
- [Discord](https://discord.gg/Tv2uQnR88V)
- [Blog](https://aider.chat/blog/)


## Kind words from users

- *The best free open source AI coding assistant.* -- [IndyDevDan](https://youtu.be/YALpX8oOn78)
- *The best AI coding assistant so far.* -- [Matthew Berman](https://www.youtube.com/watch?v=df8afeb1FY8)
- *Aider ... has easily quadrupled my coding productivity.* -- [SOLAR_FIELDS](https://news.ycombinator.com/item?id=36212100)
- *It's a cool workflow... Aider's ergonomics are perfect for me.* -- [qup](https://news.ycombinator.com/item?id=38185326)
- *It's really like having your senior developer live right in your Git repo - truly amazing!* -- [rappster](https://github.com/Aider-AI/aider/issues/124)
- *What an amazing tool. It's incredible.* -- [valyagolev](https://github.com/Aider-AI/aider/issues/6#issue-1722897858)
- *Aider is such an astounding thing!* -- [cgrothaus](https://github.com/Aider-AI/aider/issues/82#issuecomment-1631876700)
- *It was WAY faster than I would be getting off the ground and making the first few working versions.* -- [Daniel Feldman](https://twitter.com/d_feldman/status/1662295077387923456)
- *THANK YOU for Aider! It really feels like a glimpse into the future of coding.* -- [derwiki](https://news.ycombinator.com/item?id=38205643)
- *It's just amazing.  It is freeing me to do things I felt were out my comfort zone before.* -- [Dougie](https://discord.com/channels/1131200896827654144/1174002618058678323/1174084556257775656)
- *This project is stellar.* -- [funkytaco](https://github.com/Aider-AI/aider/issues/112#issuecomment-1637429008)
- *Amazing project, definitely the best AI coding assistant I've used.* -- [joshuavial](https://github.com/Aider-AI/aider/issues/84)
- *I absolutely love using Aider ... It makes software development feel so much lighter as an experience.* -- [principalideal0](https://discord.com/channels/1131200896827654144/1133421607499595858/1229689636012691468)
- *I have been recovering from multiple shoulder surgeries ... and have used aider extensively. It has allowed me to continue productivity.* -- [codeninja](https://www.reddit.com/r/OpenAI/s/nmNwkHy1zG)
- *I am an aider addict. I'm getting so much more work done, but in less time.* -- [dandandan](https://discord.com/channels/1131200896827654144/1131200896827654149/1135913253483069470)
- *After wasting $100 on tokens trying to find something better, I'm back to Aider. It blows everything else out of the water hands down, there's no competition whatsoever.* -- [SystemSculpt](https://discord.com/channels/1131200896827654144/1131200896827654149/1178736602797846548)
- *Aider is amazing, coupled with Sonnet 3.5 it’s quite mind blowing.* -- [Josh Dingus](https://discord.com/channels/1131200896827654144/1133060684540813372/1262374225298198548)
- *Hands down, this is the best AI coding assistant tool so far.* -- [IndyDevDan](https://www.youtube.com/watch?v=MPYFPvxfGZs)
- *[Aider] changed my daily coding workflows. It's mind-blowing how a single Python application can change your life.* -- [maledorak](https://discord.com/channels/1131200896827654144/1131200896827654149/1258453375620747264)
- *Best agent for actual dev work in existing codebases.* -- [Nick Dobos](https://twitter.com/NickADobos/status/1690408967963652097?s=20)
