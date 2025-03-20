<p align="center">
    <a href="https://aider.chat/"><img src="https://aider.chat/assets/logo.svg" alt="Aider Logo" width="300"></a>
</p>

<h1 align="center">
AI Pair Programming in Your Terminal
</h1>


<p align="center">
Aider lets you pair program with LLMs to start a new project or build on your existing codebase. 
</p>

<p align="center">
  <img
    src="https://aider.chat/assets/screencast.svg"
    alt="aider screencast"
  >
</p>

<p align="center">
  <a href="https://github.com/Aider-AI/aider/stargazers"><img alt="GitHub Stars" title="Total number of GitHub stars the Aider project has received" src="https://img.shields.io/github/stars/Aider-AI/aider?style=flat-square&logo=github&color=f1c40f&labelColor=555555"/></a>
  <a href="https://pypi.org/project/aider-chat/"><img alt="PyPI Downloads" title="Total number of installations via pip from PyPI" src="https://img.shields.io/badge/📦%20Installs-1.6M-2ecc71?style=flat-square&labelColor=555555"/></a>
  <img alt="Tokens per week" title="Number of tokens processed weekly by Aider users" src="https://img.shields.io/badge/📈%20Tokens%2Fweek-15B-e74c3c?style=flat-square&labelColor=555555"/>
  <a href="https://openrouter.ai/"><img alt="OpenRouter Ranking" title="Aider's ranking among applications on the OpenRouter platform" src="https://img.shields.io/badge/🏆%20OpenRouter-Top%2020-9b59b6?style=flat-square&labelColor=555555"/></a>
  <a href="https://aider.chat/HISTORY.html"><img alt="Singularity" title="Percentage of the new code in Aider's last release written by Aider itself" src="https://img.shields.io/badge/🔄%20Singularity-72%25-3498db?style=flat-square&labelColor=555555"/></a>
</p>

## Features

- 🧠 **[Cloud and local LLMs](https://aider.chat/docs/llms.html)** - Aider works best with Claude 3.7 Sonnet, DeepSeek R1 & Chat V3, OpenAI o1, o3-mini & GPT-4o, but can connect to almost any LLM, including local models.
- 🗺️ **[Maps your codebase](https://aider.chat/docs/repomap.html)** - Aider makes a map of your entire codebase, which helps it work well in larger projects.
- `</>` **[100+ code languages](https://aider.chat/docs/languages.html)** - Aider works with most popular programming languages: python, javascript, rust, ruby, go, cpp, php, html, css, and dozens more.
- 🔀 **[Git integration](https://aider.chat/docs/git.html)** - Aider automatically commits changes with sensible commit messages. Use familiar git tools to easily diff, manage and undo AI changes.
- 🖥️ **[Use in your IDE](https://aider.chat/docs/usage/watch.html)** - Use aider from within your favorite IDE or editor. Ask for changes by adding comments to your code and aider will get to work.
- 🖼️ **[Images & web pages](https://aider.chat/docs/usage/images-urls.html)** - Add images and web pages to the chat to provide visual context, screenshots, reference docs, etc.
- 🎤 **[Voice-to-code](https://aider.chat/docs/usage/voice.html)** - Speak with aider about your code! Request new features, test cases or bug fixes using your voice and let aider implement the changes.
- ✅ **[Linting & testing](https://aider.chat/docs/usage/lint-test.html)** - Automatically lint and test your code every time aider makes changes. Aider can fix problems detected by your linters and test suites.
- 📋 **[Copy/paste to web chat](https://aider.chat/docs/usage/copypaste.html)** - Work with any LLM via its web chat interface. Aider streamlines copy/pasting code context and edits back and forth with a browser.

## Getting Started

```bash
python -m pip install aider-install
aider-install

# Change directory into your codebase
cd /to/your/project

# DeepSeek
aider --model deepseek --api-key deepseek=<key>

# Claude 3.7 Sonnet
aider --model sonnet --api-key anthropic=<key>

# o3-mini
aider --model o3-mini --api-key openai=<key>
```

See the [installation instructions](https://aider.chat/docs/install.html) and [usage documentation](https://aider.chat/docs/usage.html) for more details.

## More Information

### Documentation
- [Installation Guide](https://aider.chat/docs/install.html)
- [Usage Guide](https://aider.chat/docs/usage.html)
- [Tutorial Videos](https://aider.chat/docs/usage/tutorials.html)
- [Connecting to LLMs](https://aider.chat/docs/llms.html)
- [Configuration Options](https://aider.chat/docs/config.html)
- [Troubleshooting](https://aider.chat/docs/troubleshooting.html)
- [FAQ](https://aider.chat/docs/faq.html)

### Community & Resources
- [LLM Leaderboards](https://aider.chat/docs/leaderboards/)
- [GitHub Repository](https://github.com/Aider-AI/aider)
- [Discord Community](https://discord.gg/Tv2uQnR88V)
- [Blog](https://aider.chat/blog/)

## Kind Words From Users

- *"The best free open source AI coding assistant."* — [IndyDevDan](https://youtu.be/YALpX8oOn78)
- *"The best AI coding assistant so far."* — [Matthew Berman](https://www.youtube.com/watch?v=df8afeb1FY8)
- *"Aider ... has easily quadrupled my coding productivity."* — [SOLAR_FIELDS](https://news.ycombinator.com/item?id=36212100)
- *"It's a cool workflow... Aider's ergonomics are perfect for me."* — [qup](https://news.ycombinator.com/item?id=38185326)
- *"It's really like having your senior developer live right in your Git repo - truly amazing!"* — [rappster](https://github.com/Aider-AI/aider/issues/124)
- *"What an amazing tool. It's incredible."* — [valyagolev](https://github.com/Aider-AI/aider/issues/6#issue-1722897858)
- *"Aider is such an astounding thing!"* — [cgrothaus](https://github.com/Aider-AI/aider/issues/82#issuecomment-1631876700)
- *"It was WAY faster than I would be getting off the ground and making the first few working versions."* — [Daniel Feldman](https://twitter.com/d_feldman/status/1662295077387923456)
- *"THANK YOU for Aider! It really feels like a glimpse into the future of coding."* — [derwiki](https://news.ycombinator.com/item?id=38205643)
- *"It's just amazing. It is freeing me to do things I felt were out my comfort zone before."* — [Dougie](https://discord.com/channels/1131200896827654144/1174002618058678323/1174084556257775656)
- *"This project is stellar."* — [funkytaco](https://github.com/Aider-AI/aider/issues/112#issuecomment-1637429008)
- *"Amazing project, definitely the best AI coding assistant I've used."* — [joshuavial](https://github.com/Aider-AI/aider/issues/84)
- *"I absolutely love using Aider ... It makes software development feel so much lighter as an experience."* — [principalideal0](https://discord.com/channels/1131200896827654144/1133421607499595858/1229689636012691468)
- *"I have been recovering from multiple shoulder surgeries ... and have used aider extensively. It has allowed me to continue productivity."* — [codeninja](https://www.reddit.com/r/OpenAI/s/nmNwkHy1zG)
- *"I am an aider addict. I'm getting so much more work done, but in less time."* — [dandandan](https://discord.com/channels/1131200896827654144/1131200896827654149/1135913253483069470)
- *"After wasting $100 on tokens trying to find something better, I'm back to Aider. It blows everything else out of the water hands down, there's no competition whatsoever."* — [SystemSculpt](https://discord.com/channels/1131200896827654144/1131200896827654149/1178736602797846548)
- *"Aider is amazing, coupled with Sonnet 3.5 it's quite mind blowing."* — [Josh Dingus](https://discord.com/channels/1131200896827654144/1133060684540813372/1262374225298198548)
- *"Hands down, this is the best AI coding assistant tool so far."* — [IndyDevDan](https://www.youtube.com/watch?v=MPYFPvxfGZs)
- *"[Aider] changed my daily coding workflows. It's mind-blowing how a single Python application can change your life."* — [maledorak](https://discord.com/channels/1131200896827654144/1131200896827654149/1258453375620747264)
- *"Best agent for actual dev work in existing codebases."* — [Nick Dobos](https://twitter.com/NickADobos/status/1690408967963652097?s=20)
