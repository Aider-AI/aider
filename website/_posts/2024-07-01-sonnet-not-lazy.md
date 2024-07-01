---
title: Sonnet is the opposite of lazy
excerpt: Claude 3.5 Sonnet represents a step change in AI coding.
#highlight_image: /assets/linting.jpg
draft: true
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}


# Sonnet is the opposite of lazy

[![sonnet is the opposite of lazy](/assets/sonnet-not-lazy.jpg)](https://aider.chat/assets/sonnet-not-lazy.jpg)

Claude 3.5 Sonnet represents a step change
in AI coding.
It is so industrious, diligent and hard working that
it has caused multiple problems for aider.
It's been worth the effort to adapt aider to work well
with Sonnet,
because the result is surprisingly powerful.

Sonnet's amazing work ethic caused a few problems:

1. Sonnet is capable of outputting a very large amount of correct,
complete code in one response.
So much that it can easily blow through the 4k output token limit
on API responses, which truncates its coding in mid-stream.
2. Similarly, Sonnet can specify large sequences of edits in one go, 
like changing a majority of lines while refactoring a large file.
Again, this regularly triggered the 4k output limit
and resulted in a failed edits.
3. Sonnet is not shy about quoting large chunks of an
existing file to perform a SEARCH & REPLACE edit across
a long span of lines.
This can be wasteful and also trigger the 4k output limit.


## Good problems

Problems (1) and (2) are "good problems"
in the sense that Sonnet is
able to write more high quality code than any other model!

Aider now allows Sonnet to return code in multiple 4k token
responses.
This gets all the upsides of Sonnet's prolific coding skills,
without being constrained by the 4k output token limit.


## Wasting tokens

Problem (3) does cause some real downsides.

Faced with a few small changes spread far apart in 
a source file,
Sonnet would often prefer to do one giant SEARCH/REPLACE
operation of the ~entire file.
This wastes a tremendous amount of tokens,
time and money -- and risks hitting the 4k output limit.
It would be far faster and less expensive to instead 
do a few surgical edits.

Aider now prompts Sonnet to discourage these long-winded
SEARCH/REPLACE operations
and promotes much more concise edits.


## Aider with Sonnet

[The latest release of aider](https://aider.chat/HISTORY.html#aider-v0410)
has specialized support for Claude 3.5 Sonnet:

- Aider allows Sonnet to produce as much code as it wants,
by automatically and seamlessly spreading the response
out over a sequence of 4k token API responses.
- Aider carefully prompts Sonnet to be concise and
return only changing sections of code.
This reduces Sonnet's tendency to waste time, tokens and money
returning large chunks of unchanging code.
- Aider now uses `claude-3-5-sonnet-20240620` by default if `ANTHROPIC_API_KEY` is set in the environment.

You can use aider with Sonnet like this:

```
pip install aider-chat

export ANTHROPIC_API_KEY=<key> # Mac/Linux
setx   ANTHROPIC_API_KEY <key> # Windows

aider
```

