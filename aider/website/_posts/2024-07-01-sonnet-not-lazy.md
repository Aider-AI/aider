---
title: Sonnet is the opposite of lazy
excerpt: Claude 3.5 Sonnet can easily write more good code than fits in one 4k token API response.
highlight_image: /assets/sonnet-not-lazy.jpg
nav_exclude: true
---

[![sonnet is the opposite of lazy](/assets/sonnet-not-lazy.jpg)](https://aider.chat/assets/sonnet-not-lazy.jpg)

{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Sonnet is the opposite of lazy

Claude 3.5 Sonnet represents a step change
in AI coding.
It is incredibly industrious, diligent and hard working.
Unexpectedly,
this presented a challenge:
Sonnet
was often writing so much code that
it was hitting the 4k output token limit,
truncating its coding in mid-stream.

Aider now works
around this 4k limit and allows Sonnet to produce
as much code as it wants.
The result is surprisingly powerful.
Sonnet's score on
[aider's refactoring benchmark](https://aider.chat/docs/leaderboards/#code-refactoring-leaderboard)
jumped from 55.1% up to 64.0%.
This moved Sonnet into second place, ahead of GPT-4o and
behind only Opus.

Users who tested Sonnet with a preview of 
[aider's latest release](https://aider.chat/HISTORY.html#aider-v0410)
were thrilled:

- *Works like a charm. It is a monster. It refactors files of any size like it is nothing. The continue trick with Sonnet is truly the holy grail. Aider beats [other tools] hands down. I'm going to cancel both subscriptions.* -- [Emasoft](https://github.com/paul-gauthier/aider/issues/705#issuecomment-2200338971)
- *Thanks heaps for this feature - it's a real game changer. I can be more ambitious when asking Claude for larger features.* -- [cngarrison](https://github.com/paul-gauthier/aider/issues/705#issuecomment-2196026656)
- *Fantastic...! It's such an improvement not being constrained by output token length issues. [I refactored] a single JavaScript file into seven smaller files using a single Aider request.* -- [John Galt](https://discord.com/channels/1131200896827654144/1253492379336441907/1256250487934554143)

## Hitting the 4k token output limit

All LLMs have various token limits, the most familiar being their
context window size.
But they also have a limit on how many tokens they can output
in response to a single request.
Sonnet and the majority of other
models are limited to returning 4k tokens.

Sonnet's amazing work ethic caused it to
regularly hit this 4k output token
limit for a few reasons:

1. Sonnet is capable of outputting a very large amount of correct,
complete new code in one response.
2. Similarly, Sonnet can specify long sequences of edits in one go, 
like changing a majority of lines while refactoring a large file.
3. Sonnet tends to quote large chunks of a
file when performing a SEARCH & REPLACE edits.
Beyond token limits, this is very wasteful.

## Good problems

Problems (1) and (2) are "good problems"
in the sense that Sonnet is
able to write more high quality code than any other model!
We just don't want it to be interrupted prematurely
by the 4k output limit.

Aider now allows Sonnet to return code in multiple 4k token
responses.
Aider seamlessly combines them so that Sonnet can return arbitrarily
long responses.
This gets all the upsides of Sonnet's prolific coding skills,
without being constrained by the 4k output token limit.


## Wasting tokens

Problem (3) is more complicated, as Sonnet isn't just
being stopped early -- it's actually wasting a lot
of tokens, time and money.

Faced with a few small changes spread far apart in 
a source file,
Sonnet would often prefer to do one giant SEARCH/REPLACE
operation of almost the entire file.
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
- Aider carefully prompts Sonnet to be concise when proposing
code edits.
This reduces Sonnet's tendency to waste time, tokens and money
returning large chunks of unchanging code.
- Aider now uses Claude 3.5 Sonnet by default if the `ANTHROPIC_API_KEY` is set in the environment.

See 
[aider's install instructions](https://aider.chat/docs/install.html)
for more details, but
you can get started quickly with aider and Sonnet like this:

```
$ python -m pip install aider-chat

$ export ANTHROPIC_API_KEY=<key> # Mac/Linux
$ setx   ANTHROPIC_API_KEY <key> # Windows, restart shell after setx

$ aider
```

