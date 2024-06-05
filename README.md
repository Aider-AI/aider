

# Aider is AI pair programming in your terminal

Aider lets you pair program with LLMs,
to edit code in your local git repository.
Aider edits the code in your local source files,
and [git commits the changes](https://aider.chat/docs/faq.html#how-does-aider-use-git).
Start a new project or work with an existing git repo.
Aider works well with GPT-4o, Claude 3 Opus, GPT-3.5
and can [connect to almost any LLM](https://aider.chat/docs/llms.html).

<p align="center">
  <img src="website/assets/screencast.svg" alt="aider screencast">
</p>

<p align="center">
  <a href="https://discord.gg/Tv2uQnR88V">
    <img src="https://img.shields.io/badge/Join-Discord-blue.svg"/>
  </a>
</p>

## Getting started

See the
[installation instructions](https://aider.chat/docs/install.html)
for more details, but you can
get started quickly like this:

```
$ pip install aider-chat

# To work with GPT-4o
$ export OPENAI_API_KEY=your-key-goes-here
$ aider 

# To work with Claude 3 Opus:
$ export ANTHROPIC_API_KEY=your-key-goes-here
$ aider --opus
```


## Features

- Chat with aider about your code by running `aider <file1> <file2> ...`
- Aider will edit the content of your source files.
- Aider works with most popular languages: python, javascript, typescript, php, html, css, and more...
- Aider works well with GPT-4o, Claude 3 Opus, GPT-3.5 and supports [connecting to almost any LLM](https://aider.chat/docs/llms.html).
- Request new features, changes, improvements, or bug fixes to your code.
- Ask for new test cases, updated documentation or code refactors.
- Paste in GitHub issue URLs and aider will try and solve them.
- Aider [automatically git commits changes](https://aider.chat/docs/faq.html#how-does-aider-use-git) These frequent, automatic commits provide a safety net. It's easy to undo changes or use standard git workflows to manage longer sequences of changes.
- Aider can make coordinated changes across multiple files at once.
- Aider uses a [map of your entire git repo](https://aider.chat/docs/repomap.html), which helps it work well in larger codebases.
- You can also edit files in your editor while chatting with aider.
Aider will notice your changes and always use the latest version.
So you can bounce back and forth between aider and your editor, to collaboratively code with AI.
- You can add images to the chat (GPT-4o, GPT-4 Turbo, etc).
- You can add URLs to the chat and aider will read their content.


## Documentation

- [Installation](https://aider.chat/docs/install.html)
- [Usage](https://aider.chat/docs/usage.html)
- [Tutorial videos](https://aider.chat/docs/tutorials.html)
- [Connecting to LLMs](https://aider.chat/docs/llms.html)
- [LLM Leaderboards](https://aider.chat/docs/leaderboards/)
- [FAQ](https://aider.chat/docs/faq.html)
- [Discord](https://discord.gg/Tv2uQnR88V)
- [Blog](https://aider.chat/blog/)


## Kind words from users

- *The best AI coding assistant so far.* -- [Matthew Berman](https://www.youtube.com/watch?v=df8afeb1FY8)
- *Hands down, this is the best AI coding assistant tool so far.* -- [IndyDevDan](https://www.youtube.com/watch?v=MPYFPvxfGZs)
- *Aider ... has easily quadrupled my coding productivity.* -- [SOLAR_FIELDS](https://news.ycombinator.com/item?id=36212100)
- *It's a cool workflow... Aider's ergonomics are perfect for me.* -- [qup](https://news.ycombinator.com/item?id=38185326)
- *It's really like having your senior developer live right in your Git repo - truly amazing!* -- [rappster](https://github.com/paul-gauthier/aider/issues/124)
- *What an amazing tool. It's incredible.* -- [valyagolev](https://github.com/paul-gauthier/aider/issues/6#issue-1722897858)
- *Aider is such an astounding thing!* -- [cgrothaus](https://github.com/paul-gauthier/aider/issues/82#issuecomment-1631876700)
- *It was WAY faster than I would be getting off the ground and making the first few working versions.* -- [Daniel Feldman](https://twitter.com/d_feldman/status/1662295077387923456)
- *THANK YOU for Aider! It really feels like a glimpse into the future of coding.* -- [derwiki](https://news.ycombinator.com/item?id=38205643)
- *It's just amazing.  It is freeing me to do things I felt were out my comfort zone before.* -- [Dougie](https://discord.com/channels/1131200896827654144/1174002618058678323/1174084556257775656)
- *This project is stellar.* -- [funkytaco](https://github.com/paul-gauthier/aider/issues/112#issuecomment-1637429008)
- *Amazing project, definitely the best AI coding assistant I've used.* -- [joshuavial](https://github.com/paul-gauthier/aider/issues/84)
- *I absolutely love using Aider ... It makes software development feel so much lighter as an experience.* -- [principalideal0](https://discord.com/channels/1131200896827654144/1133421607499595858/1229689636012691468)
- *I have been recovering from multiple shoulder surgeries ... and have used aider extensively. It has allowed me to continue productivity.* -- [codeninja](https://www.reddit.com/r/OpenAI/s/nmNwkHy1zG)
- *I am an aider addict. I'm getting so much more work done, but in less time.* -- [dandandan](https://discord.com/channels/1131200896827654144/1131200896827654149/1135913253483069470)
- *After wasting $100 on tokens trying to find something better, I'm back to Aider. It blows everything else out of the water hands down, there's no competition whatsoever.* -- [SystemSculpt](https://discord.com/channels/1131200896827654144/1131200896827654149/1178736602797846548)
- *Best agent for actual dev work in existing codebases.* -- [Nick Dobos](https://twitter.com/NickADobos/status/1690408967963652097?s=20)
