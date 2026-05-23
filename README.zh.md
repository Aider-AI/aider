<p align="center">
    <a href="https://aider.chat/"><img src="https://aider.chat/assets/logo.svg" alt="Aider Logo" width="300"></a>
</p>

<h1 align="center">
终端里的 AI 结对编程助手
</h1>

<p align="center">
Aider 让你能够与大语言模型 (LLMs) 结对编程，无论是开启新项目还是在现有代码库上进行开发。
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
  <a href="https://github.com/Aider-AI/aider/stargazers"><img alt="GitHub Stars" title="Aider 项目在 GitHub 上的总星标数"
src="https://img.shields.io/github/stars/Aider-AI/aider?style=flat-square&logo=github&color=f1c40f&labelColor=555555"/></a>
  <a href="https://pypi.org/project/aider-chat/"><img alt="PyPI Downloads" title="通过 PyPI 使用 pip 安装的总次数"
src="https://img.shields.io/badge/📦%20安装量-5.3M-2ecc71?style=flat-square&labelColor=555555"/></a>
  <img alt="Tokens per week" title="Aider 用户每周处理的 token 数量"
src="https://img.shields.io/badge/📈%20每周%20Tokens-15B-3498db?style=flat-square&labelColor=555555"/>
  <a href="https://openrouter.ai/#options-menu"><img alt="OpenRouter Ranking" title="Aider 在 OpenRouter 平台上的应用排名"
src="https://img.shields.io/badge/🏆%20OpenRouter-Top%2020-9b59b6?style=flat-square&labelColor=555555"/></a>
  <a href="https://aider.chat/HISTORY.html"><img alt="Singularity" title="Aider 最新版本中由 Aider 自身编写的新代码比例"
src="https://img.shields.io/badge/🔄%20奇点-88%25-e74c3c?style=flat-square&labelColor=555555"/></a>
<!--[[[end]]]-->  
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <strong>中文</strong>
</p>

## 核心功能

### [支持云端和本地 LLM](https://aider.chat/docs/llms.html)

<a href="https://aider.chat/docs/llms.html"><img src="https://aider.chat/assets/icons/brain.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Aider 与 Claude 3.7 Sonnet, DeepSeek R1 & Chat V3, OpenAI o1, o3-mini & GPT-4o 的配合最为默契，但也能够连接到几乎所有的 LLM，包括本地运行的模型。

<br>

### [构建代码库地图](https://aider.chat/docs/repomap.html)

<a href="https://aider.chat/docs/repomap.html"><img src="https://aider.chat/assets/icons/map-outline.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Aider 会为你的整个代码库绘制一张地图 (map)，这使得它在处理大型项目时游刃有余。

<br>

### [支持 100+ 种编程语言](https://aider.chat/docs/languages.html)

<a href="https://aider.chat/docs/languages.html"><img src="https://aider.chat/assets/icons/code-tags.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Aider 支持绝大多数主流的编程语言：python, javascript, rust, ruby, go, cpp, php, html, css 以及数十种其他语言。

<br>

### [Git 深度集成](https://aider.chat/docs/git.html)

<a href="https://aider.chat/docs/git.html"><img src="https://aider.chat/assets/icons/source-branch.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
Aider 会使用合理的 commit message 自动提交修改。你可以使用熟悉的 git 工具来轻松地比对 (diff)、管理和撤销 AI 带来的代码变更。

<br>

### [在 IDE 中使用](https://aider.chat/docs/usage/watch.html)

<a href="https://aider.chat/docs/usage/watch.html"><img src="https://aider.chat/assets/icons/monitor.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
在你最喜欢的 IDE 或编辑器中无缝使用 aider。只需在代码中添加注释提出修改需求，aider 就会自动开始工作。

<br>

### [图像与网页支持](https://aider.chat/docs/usage/images-urls.html)

<a href="https://aider.chat/docs/usage/images-urls.html"><img src="https://aider.chat/assets/icons/image-multiple.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
你可以将图像和网页链接添加到聊天中，为 AI 提供视觉上下文、屏幕截图、参考文档等信息。

<br>

### [语音转代码 (Voice-to-code)](https://aider.chat/docs/usage/voice.html)

<a href="https://aider.chat/docs/usage/voice.html"><img src="https://aider.chat/assets/icons/microphone.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
直接用语音和 aider 讨论你的代码！使用语音提出新功能、测试用例或 bug 修复的请求，让 aider 替你实现代码。

<br>

### [Linting 与测试](https://aider.chat/docs/usage/lint-test.html)

<a href="https://aider.chat/docs/usage/lint-test.html"><img src="https://aider.chat/assets/icons/check-all.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
每当 aider 修改代码时，自动运行 lint 和测试。Aider 可以自动修复你的 linter 和测试套件发现的问题。

<br>

### [Web 聊天界面的复制/粘贴支持](https://aider.chat/docs/usage/copypaste.html)

<a href="https://aider.chat/docs/usage/copypaste.html"><img src="https://aider.chat/assets/icons/content-copy.svg" width="32" height="32" align="left" valign="middle" style="margin-right:10px"></a>
通过其 Web 聊天界面与任何 LLM 协作。Aider 简化了在浏览器和代码环境之间来回复制/粘贴代码上下文和修改片段的流程。

## 快速开始

```bash
python -m pip install aider-install
aider-install

# 切换到你的代码库目录
cd /to/your/project

# DeepSeek
aider --model deepseek --api-key deepseek=<key>

# Claude 3.7 Sonnet
aider --model sonnet --api-key anthropic=<key>

# o3-mini
aider --model o3-mini --api-key openai=<key>
```

更多详细信息，请参阅[安装指南](https://aider.chat/docs/install.html)和[使用文档](https://aider.chat/docs/usage.html)。

## 更多信息

### 文档
- [安装指南](https://aider.chat/docs/install.html)
- [使用指南](https://aider.chat/docs/usage.html)
- [教程视频](https://aider.chat/docs/usage/tutorials.html)
- [连接到不同的 LLM](https://aider.chat/docs/llms.html)
- [配置选项](https://aider.chat/docs/config.html)
- [故障排除](https://aider.chat/docs/troubleshooting.html)
- [常见问题 (FAQ)](https://aider.chat/docs/faq.html)

### 社区与资源
- [LLM 排行榜](https://aider.chat/docs/leaderboards/)
- [GitHub 仓库](https://github.com/Aider-AI/aider)
- [Discord 社区](https://discord.gg/Y7X7bhMQFV)
- [发布说明](https://aider.chat/HISTORY.html)
- [官方博客](https://aider.chat/blog/)

## 用户真实评价

- *"My life has changed... Aider... It's going to rock your world."* — [Eric S. Raymond on X](https://x.com/esrtweet/status/1910809356381413593)
- *"The best free open source AI coding assistant."* — [IndyDevDan on YouTube](https://youtu.be/YALpX8oOn78)
- *"The best AI coding assistant so far."* — [Matthew Berman on YouTube](https://www.youtube.com/watch?v=df8afeb1FY8)
- *"Aider ... has easily quadrupled my coding productivity."* — [SOLAR_FIELDS on Hacker News](https://news.ycombinator.com/item?id=36212100)
- *"It's a cool workflow... Aider's ergonomics are perfect for me."* — [qup on Hacker News](https://news.ycombinator.com/item?id=38185326)
- *"It's really like having your senior developer live right in your Git repo - truly amazing!"* — [rappster on GitHub](https://github.com/Aider-AI/aider/issues/124)
- *"What an amazing tool. It's incredible."* — [valyagolev on GitHub](https://github.com/Aider-AI/aider/issues/6#issue-1722897858)
