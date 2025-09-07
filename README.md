## Fork Additions

This project aims to be compatible with upstream Aider, but with priority commits merged in and with some opportunistic bug fixes and optimizations

### Merged PRs

* [MCP: #3937](https://github.com/Aider-AI/aider/pull/3937)
    * [MCP Multi Tool Response](https://github.com/quinlanjager/aider/pull/1)
* [Navigator Mode: #3781](https://github.com/Aider-AI/aider/pull/3781)
    * [Navigator Mode Large File Count](https://github.com/Aider-AI/aider/commit/b88a7bda649931798209945d9687718316c7427f)
* [Qwen 3: #4383](https://github.com/Aider-AI/aider/pull/4383)
* [Fuzzy Search: #4366](https://github.com/Aider-AI/aider/pull/4366)
* [Map Cache Location Config: #2911](https://github.com/Aider-AI/aider/pull/2911)
* [Enhanced System Prompts: #3804](https://github.com/Aider-AI/aider/pull/3804)
* [Repo Map File Name Truncation Fix: #4320](https://github.com/Aider-AI/aider/pull/4320)
* [Read Only Stub Files For Context Window Management : #3056](https://github.com/Aider-AI/aider/pull/3056)

### Other Updates

* [Added Remote MCP Tool Calls With HTTP Streaming](https://github.com/Aider-AI/aider/commit/a86039f73579df7c32fee910967827c9fccdec0d)
    * [Enforce single tool call at a time](https://github.com/Aider-AI/aider/commit/3346c3e6194096cef64b1899b017bde36a65f794)
    * [Upgraded MCP dep to 1.12.3 for Remote MCP Tool Calls](https://github.com/dwash96/aider-ce/commit/a91ee1c03627a31093364fd2a09e654781b1b879)
    * [Updated base Python version to 3.12 to better support navigator mode (might consider undoing this, if dependency list supports it)](https://github.com/dwash96/aider-ce/commit/9ed416d523c11362a3ba9fc4c02134e0e79d41fc)
* [Suppress LiteLLM asyncio errors that clutter output](https://github.com/Aider-AI/aider/issues/6)
* [Updated Docker File Build Process](https://github.com/Aider-AI/aider/commit/cbab01458d0a35c03b30ac2f6347a74fc2b9f662)
    * [Manually install necessary ubuntu dependencies](https://github.com/dwash96/aider-ce/issues/14)
* [.gitignore updates](https://github.com/dwash96/aider-ce/commit/7c7e803fa63d1acd860eef1423e5a03220df6017)
* [Experimental Context Compaction For Longer Running Generation Tasks](https://github.com/Aider-AI/aider/issues/6)
* [Edit Before Adding Files and Reflecting](https://github.com/dwash96/aider-ce/pull/22)
* [Fix Deepseek model configurations](https://github.com/Aider-AI/aider/commit/c839a6dd8964d702172cae007375e299732d3823)
* [Relax Version Pinning For Easier Distribution](https://github.com/dwash96/aider-ce/issues/18)
* [Remove Confirm Responses from History](https://github.com/Aider-AI/aider/pull/3958)

### Other Notes
* [MCP Configuration](https://github.com/dwash96/aider-ce/blob/main/aider/website/docs/config/mcp.md)

### Installation Instructions
This project should be installable using the commands

```
pip install aider-ce
```

or

```
uv pip install aider-ce
```

The package exports an `aider-ce` command that accepts all of Aider's configuration options

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
from scripts.homepage import get_badges_md
text = get_badges_md()
cog.out(text)
]]]-->
  <a href="https://github.com/Aider-AI/aider/stargazers"><img alt="GitHub Stars" title="Total number of GitHub stars the Aider project has received"
src="https://img.shields.io/github/stars/Aider-AI/aider?style=flat-square&logo=github&color=f1c40f&labelColor=555555"/></a>
  <a href="https://pypi.org/project/aider-chat/"><img alt="PyPI Downloads" title="Total number of installations via pip from PyPI"
src="https://img.shields.io/badge/📦%20Installs-3.0M-2ecc71?style=flat-square&labelColor=555555"/></a>
  <img alt="Tokens per week" title="Number of tokens processed weekly by Aider users"
src="https://img.shields.io/badge/📈%20Tokens%2Fweek-15B-3498db?style=flat-square&labelColor=555555"/>
  <a href="https://openrouter.ai/#options-menu"><img alt="OpenRouter Ranking" title="Aider's ranking among applications on the OpenRouter platform"
src="https://img.shields.io/badge/🏆%20OpenRouter-Top%2020-9b59b6?style=flat-square&labelColor=555555"/></a>
  <a href="https://aider.chat/HISTORY.html"><img alt="Singularity" title="Percentage of the new code in Aider's last release written by Aider itself"
src="https://img.shields.io/badge/🔄%20Singularity-88%25-e74c3c?style=flat-square&labelColor=555555"/></a>
<!--[[[end]]]-->  
</p>

## Features

### [Cloud and local LLMs](https://aider.chat/docs/llms.html)

<a href="https://aider.chat/docs/llms.html"><img src="https://aider.chat/assets/icons/brain.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Aider works best with Claude 3.7 Sonnet, DeepSeek R1 & Chat V3, OpenAI o1, o3-mini & GPT-4o, but can connect to almost any LLM, including local models.

<br>

### [Maps your codebase](https://aider.chat/docs/repomap.html)

<a href="https://aider.chat/docs/repomap.html"><img src="https://aider.chat/assets/icons/map-outline.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Aider makes a map of your entire codebase, which helps it work well in larger projects.

<br>

### [100+ code languages](https://aider.chat/docs/languages.html)

<a href="https://aider.chat/docs/languages.html"><img src="https://aider.chat/assets/icons/code-tags.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Aider works with most popular programming languages: python, javascript, rust, ruby, go, cpp, php, html, css, and dozens more.

<br>

### [Git integration](https://aider.chat/docs/git.html)

<a href="https://aider.chat/docs/git.html"><img src="https://aider.chat/assets/icons/source-branch.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Aider automatically commits changes with sensible commit messages. Use familiar git tools to easily diff, manage and undo AI changes.

<br>

### [Use in your IDE](https://aider.chat/docs/usage/watch.html)

<a href="https://aider.chat/docs/usage/watch.html"><img src="https://aider.chat/assets/icons/monitor.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Use aider from within your favorite IDE or editor. Ask for changes by adding comments to your code and aider will get to work.

<br>

### [Images & web pages](https://aider.chat/docs/usage/images-urls.html)

<a href="https://aider.chat/docs/usage/images-urls.html"><img src="https://aider.chat/assets/icons/image-multiple.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Add images and web pages to the chat to provide visual context, screenshots, reference docs, etc.

<br>

### [Voice-to-code](https://aider.chat/docs/usage/voice.html)

<a href="https://aider.chat/docs/usage/voice.html"><img src="https://aider.chat/assets/icons/microphone.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Speak with aider about your code! Request new features, test cases or bug fixes using your voice and let aider implement the changes.

<br>

### [Linting & testing](https://aider.chat/docs/usage/lint-test.html)

<a href="https://aider.chat/docs/usage/lint-test.html"><img src="https://aider.chat/assets/icons/check-all.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Automatically lint and test your code every time aider makes changes. Aider can fix problems detected by your linters and test suites.

<br>

### [Copy/paste to web chat](https://aider.chat/docs/usage/copypaste.html)

<a href="https://aider.chat/docs/usage/copypaste.html"><img src="https://aider.chat/assets/icons/content-copy.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Work with any LLM via its web chat interface. Aider streamlines copy/pasting code context and edits back and forth with a browser.

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
- [Discord Community](https://discord.gg/Y7X7bhMQFV)
- [Release notes](https://aider.chat/HISTORY.html)
- [Blog](https://aider.chat/blog/)

## Kind Words From Users

- *"My life has changed... Aider... It's going to rock your world."* — [Eric S. Raymond on X](https://x.com/esrtweet/status/1910809356381413593)
- *"The best free open source AI coding assistant."* — [IndyDevDan on YouTube](https://youtu.be/YALpX8oOn78)
- *"The best AI coding assistant so far."* — [Matthew Berman on YouTube](https://www.youtube.com/watch?v=df8afeb1FY8)
- *"Aider ... has easily quadrupled my coding productivity."* — [SOLAR_FIELDS on Hacker News](https://news.ycombinator.com/item?id=36212100)
- *"It's a cool workflow... Aider's ergonomics are perfect for me."* — [qup on Hacker News](https://news.ycombinator.com/item?id=38185326)
- *"It's really like having your senior developer live right in your Git repo - truly amazing!"* — [rappster on GitHub](https://github.com/Aider-AI/aider/issues/124)
- *"What an amazing tool. It's incredible."* — [valyagolev on GitHub](https://github.com/Aider-AI/aider/issues/6#issue-1722897858)
- *"Aider is such an astounding thing!"* — [cgrothaus on GitHub](https://github.com/Aider-AI/aider/issues/82#issuecomment-1631876700)
- *"It was WAY faster than I would be getting off the ground and making the first few working versions."* — [Daniel Feldman on X](https://twitter.com/d_feldman/status/1662295077387923456)
- *"THANK YOU for Aider! It really feels like a glimpse into the future of coding."* — [derwiki on Hacker News](https://news.ycombinator.com/item?id=38205643)
- *"It's just amazing. It is freeing me to do things I felt were out my comfort zone before."* — [Dougie on Discord](https://discord.com/channels/1131200896827654144/1174002618058678323/1174084556257775656)
- *"This project is stellar."* — [funkytaco on GitHub](https://github.com/Aider-AI/aider/issues/112#issuecomment-1637429008)
- *"Amazing project, definitely the best AI coding assistant I've used."* — [joshuavial on GitHub](https://github.com/Aider-AI/aider/issues/84)
- *"I absolutely love using Aider ... It makes software development feel so much lighter as an experience."* — [principalideal0 on Discord](https://discord.com/channels/1131200896827654144/1133421607499595858/1229689636012691468)
- *"I have been recovering from ... surgeries ... aider ... has allowed me to continue productivity."* — [codeninja on Reddit](https://www.reddit.com/r/OpenAI/s/nmNwkHy1zG)
- *"I am an aider addict. I'm getting so much more work done, but in less time."* — [dandandan on Discord](https://discord.com/channels/1131200896827654144/1131200896827654149/1135913253483069470)
- *"Aider... blows everything else out of the water hands down, there's no competition whatsoever."* — [SystemSculpt on Discord](https://discord.com/channels/1131200896827654144/1131200896827654149/1178736602797846548)
- *"Aider is amazing, coupled with Sonnet 3.5 it's quite mind blowing."* — [Josh Dingus on Discord](https://discord.com/channels/1131200896827654144/1133060684540813372/1262374225298198548)
- *"Hands down, this is the best AI coding assistant tool so far."* — [IndyDevDan on YouTube](https://www.youtube.com/watch?v=MPYFPvxfGZs)
- *"[Aider] changed my daily coding workflows. It's mind-blowing how ...(it)... can change your life."* — [maledorak on Discord](https://discord.com/channels/1131200896827654144/1131200896827654149/1258453375620747264)
- *"Best agent for actual dev work in existing codebases."* — [Nick Dobos on X](https://twitter.com/NickADobos/status/1690408967963652097?s=20)
- *"One of my favorite pieces of software. Blazing trails on new paradigms!"* — [Chris Wall on X](https://x.com/chris65536/status/1905053299251798432)
- *"Aider has been revolutionary for me and my work."* — [Starry Hope on X](https://x.com/starryhopeblog/status/1904985812137132056)
- *"Try aider! One of the best ways to vibe code."* — [Chris Wall on X](https://x.com/Chris65536/status/1905053418961391929)
- *"Freaking love Aider."* — [hztar on Hacker News](https://news.ycombinator.com/item?id=44035015)
- *"Aider is hands down the best. And it's free and opensource."* — [AriyaSavakaLurker on Reddit](https://www.reddit.com/r/ChatGPTCoding/comments/1ik16y6/whats_your_take_on_aider/mbip39n/)
- *"Aider is also my best friend."* — [jzn21 on Reddit](https://www.reddit.com/r/ChatGPTCoding/comments/1heuvuo/aider_vs_cline_vs_windsurf_vs_cursor/m27dcnb/)
- *"Try Aider, it's worth it."* — [jorgejhms on Reddit](https://www.reddit.com/r/ChatGPTCoding/comments/1heuvuo/aider_vs_cline_vs_windsurf_vs_cursor/m27cp99/)
- *"I like aider :)"* — [Chenwei Cui on X](https://x.com/ccui42/status/1904965344999145698)
- *"Aider is the precision tool of LLM code gen... Minimal, thoughtful and capable of surgical changes ... while keeping the developer in control."* — [Reilly Sweetland on X](https://x.com/rsweetland/status/1904963807237259586)
- *"Cannot believe aider vibe coded a 650 LOC feature across service and cli today in 1 shot."* - [autopoietist on Discord](https://discord.com/channels/1131200896827654144/1131200896827654149/1355675042259796101)
- *"Oh no the secret is out! Yes, Aider is the best coding tool around. I highly, highly recommend it to anyone."* — [Joshua D Vander Hook on X](https://x.com/jodavaho/status/1911154899057795218)
- *"thanks to aider, i have started and finished three personal projects within the last two days"* — [joseph stalzyn on X](https://x.com/anitaheeder/status/1908338609645904160)
- *"Been using aider as my daily driver for over a year ... I absolutely love the tool, like beyond words."* — [koleok on Discord](https://discord.com/channels/1131200896827654144/1273248471394291754/1356727448372252783)
- *"Aider ... is the tool to benchmark against."* — [BeetleB on Hacker News](https://news.ycombinator.com/item?id=43930201)
- *"aider is really cool"* — [kache on X](https://x.com/yacineMTB/status/1911224442430124387)

