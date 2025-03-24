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
<!--[[[cog
from scripts.badges import get_badges_md
text = get_badges_md()
cog.out(text)
]]]-->
  <a href="https://github.com/Aider-AI/aider/stargazers"><img alt="GitHub Stars" title="Total number of GitHub stars the Aider project has received"
src="https://img.shields.io/github/stars/Aider-AI/aider?style=flat-square&logo=github&color=f1c40f&labelColor=555555"/></a>
  <a href="https://pypi.org/project/aider-chat/"><img alt="PyPI Downloads" title="Total number of installations via pip from PyPI"
src="https://img.shields.io/badge/📦%20Installs-1.7M-2ecc71?style=flat-square&labelColor=555555"/></a>
  <img alt="Tokens per week" title="Number of tokens processed weekly by Aider users"
src="https://img.shields.io/badge/📈%20Tokens%2Fweek-15B-3498db?style=flat-square&labelColor=555555"/>
  <a href="https://openrouter.ai/"><img alt="OpenRouter Ranking" title="Aider's ranking among applications on the OpenRouter platform"
src="https://img.shields.io/badge/🏆%20OpenRouter-Top%2020-9b59b6?style=flat-square&labelColor=555555"/></a>
  <a href="https://aider.chat/HISTORY.html"><img alt="Singularity" title="Percentage of the new code in Aider's last release written by Aider itself"
src="https://img.shields.io/badge/🔄%20Singularity-92%25-e74c3c?style=flat-square&labelColor=555555"/></a>
<!--[[[end]]]-->  
</p>

## Features

- <svg class="mdi-icon" style="width:1em;height:1em;vertical-align:-0.2em" viewBox="0 0 24 24"><path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A7,7 0 0,1 21,14H22V18H20V20H17V18H13V16H14A5,5 0 0,0 19,11H13V8H11V19H9V11H5A5,5 0 0,0 10,16H11V18H7V20H4V18H2V14H3A7,7 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2Z" fill="currentColor"/></svg> **[Cloud and local LLMs](https://aider.chat/docs/llms.html)** - Aider works best with Claude 3.7 Sonnet, DeepSeek R1 & Chat V3, OpenAI o1, o3-mini & GPT-4o, but can connect to almost any LLM, including local models.
- <svg class="mdi-icon" style="width:1em;height:1em;vertical-align:-0.2em" viewBox="0 0 24 24"><path d="M9,3L5,7H8V14H10V7H13M16,17V10H14V17H11L15,21L19,17H16Z" fill="currentColor"/></svg> **[Maps your codebase](https://aider.chat/docs/repomap.html)** - Aider makes a map of your entire codebase, which helps it work well in larger projects.
- <svg class="mdi-icon" style="width:1em;height:1em;vertical-align:-0.2em" viewBox="0 0 24 24"><path d="M14.6,16.6L19.2,12L14.6,7.4L16,6L22,12L16,18L14.6,16.6M9.4,16.6L4.8,12L9.4,7.4L8,6L2,12L8,18L9.4,16.6Z" fill="currentColor"/></svg> **[100+ code languages](https://aider.chat/docs/languages.html)** - Aider works with most popular programming languages: python, javascript, rust, ruby, go, cpp, php, html, css, and dozens more.
- <svg class="mdi-icon" style="width:1em;height:1em;vertical-align:-0.2em" viewBox="0 0 24 24"><path d="M7,14A2,2 0 0,1 5,12A2,2 0 0,1 7,10A2,2 0 0,1 9,12A2,2 0 0,1 7,14M12.65,10C11.83,7.67 9.61,6 7,6A6,6 0 0,0 1,12A6,6 0 0,0 7,18C9.61,18 11.83,16.33 12.65,14H17V18H21V14H23V10H12.65Z" fill="currentColor"/></svg> **[Git integration](https://aider.chat/docs/git.html)** - Aider automatically commits changes with sensible commit messages. Use familiar git tools to easily diff, manage and undo AI changes.
- <svg class="mdi-icon" style="width:1em;height:1em;vertical-align:-0.2em" viewBox="0 0 24 24"><path d="M21,16H3V4H21M21,2H3C1.89,2 1,2.89 1,4V16A2,2 0 0,0 3,18H10V20H8V22H16V20H14V18H21A2,2 0 0,0 23,16V4C23,2.89 22.1,2 21,2Z" fill="currentColor"/></svg> **[Use in your IDE](https://aider.chat/docs/usage/watch.html)** - Use aider from within your favorite IDE or editor. Ask for changes by adding comments to your code and aider will get to work.
- <svg class="mdi-icon" style="width:1em;height:1em;vertical-align:-0.2em" viewBox="0 0 24 24"><path d="M8.5,13.5L11,16.5L14.5,12L19,18H5M21,19V5C21,3.89 20.1,3 19,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19Z" fill="currentColor"/></svg> **[Images & web pages](https://aider.chat/docs/usage/images-urls.html)** - Add images and web pages to the chat to provide visual context, screenshots, reference docs, etc.
- <svg class="mdi-icon" style="width:1em;height:1em;vertical-align:-0.2em" viewBox="0 0 24 24"><path d="M12,2A3,3 0 0,1 15,5V11A3,3 0 0,1 12,14A3,3 0 0,1 9,11V5A3,3 0 0,1 12,2M19,11C19,14.53 16.39,17.44 13,17.93V21H11V17.93C7.61,17.44 5,14.53 5,11H7A5,5 0 0,0 12,16A5,5 0 0,0 17,11H19Z" fill="currentColor"/></svg> **[Voice-to-code](https://aider.chat/docs/usage/voice.html)** - Speak with aider about your code! Request new features, test cases or bug fixes using your voice and let aider implement the changes.
- <svg class="mdi-icon" style="width:1em;height:1em;vertical-align:-0.2em" viewBox="0 0 24 24"><path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z" fill="currentColor"/></svg> **[Linting & testing](https://aider.chat/docs/usage/lint-test.html)** - Automatically lint and test your code every time aider makes changes. Aider can fix problems detected by your linters and test suites.
- <svg class="mdi-icon" style="width:1em;height:1em;vertical-align:-0.2em" viewBox="0 0 24 24"><path d="M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z" fill="currentColor"/></svg> **[Copy/paste to web chat](https://aider.chat/docs/usage/copypaste.html)** - Work with any LLM via its web chat interface. Aider streamlines copy/pasting code context and edits back and forth with a browser.

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
