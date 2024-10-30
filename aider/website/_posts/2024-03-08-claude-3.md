---
title: Claude 3 beats GPT-4 on Aider's code editing benchmark
excerpt: Claude 3 Opus outperforms all of OpenAI's models on Aider's code editing benchmark, making it the best available model for pair programming with AI.
highlight_image: /assets/2024-03-07-claude-3.jpg
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Claude 3 beats GPT-4 on Aider's code editing benchmark

[![benchmark results](/assets/2024-03-07-claude-3.svg)](https://aider.chat/assets/2024-03-07-claude-3.svg)

[Anthropic just released their new Claude 3 models](https://www.anthropic.com/news/claude-3-family)
with evals showing better performance on coding tasks.
With that in mind, I've been benchmarking the new models
using Aider's code editing benchmark suite.

Claude 3 Opus outperforms all of OpenAI's models,
making it the best available model for pair programming with AI.

To use Claude 3 Opus with aider:

```
python -m pip install -U aider-chat
export ANTHROPIC_API_KEY=sk-...
aider --opus
```

## Aider's code editing benchmark

[Aider](https://github.com/Aider-AI/aider)
is an open source command line chat tool that lets you
pair program with AI on code in your local git repo.

Aider relies on a
[code editing benchmark](https://aider.chat/docs/benchmarks.html)
to quantitatively evaluate how well
an LLM can make changes to existing code.
The benchmark uses aider to try and complete
[133 Exercism Python coding exercises](https://github.com/exercism/python).
For each exercise,
Exercism provides a starting python file with stubs for the needed functions,
a natural language description of the problem to solve
and a test suite to evaluate whether the coder has correctly solved the problem.

The LLM gets two tries to solve each problem:

1. On the first try, it gets the initial stub code and the English description of the coding task. If the tests all pass, we are done.
2. If any tests failed, aider sends the LLM the failing test output and gives it a second try to complete the task.

## Benchmark results

### Claude 3 Opus

- The new `claude-3-opus-20240229` model got the highest score ever on this benchmark, completing 68.4% of the tasks with two tries.
- Its single-try performance was comparable to the latest GPT-4 Turbo model `gpt-4-0125-preview`, at 54.1%.
- While Opus got the highest score, it was only a few points higher than the GPT-4 Turbo results. Given the extra costs of Opus and the slower response times, it remains to be seen which is the most practical model for daily coding use.

### Claude 3 Sonnet

- The new `claude-3-sonnet-20240229` model performed similarly to OpenAI's GPT-3.5 Turbo models with an overall score of 54.9% and a first-try score of 43.6%.

## Code editing

It's highly desirable to have the LLM send back code edits as
some form of diffs, rather than having it send back an updated copy of the
entire source code.

Weaker models like GPT-3.5 are unable to use diffs, and are stuck sending back
updated copies of entire source files.
Aider uses more efficient
[search/replace blocks](https://aider.chat/2023/07/02/benchmarks.html#diff)
with the original GPT-4
and
[unified diffs](https://aider.chat/2023/12/21/unified-diffs.html#unified-diff-editing-format)
with the newer GPT-4 Turbo models.

Claude 3 Opus works best with the search/replace blocks, allowing it to send back
code changes efficiently.
Unfortunately, the Sonnet model was only able to work reliably with whole files,
which limits it to editing smaller source files and uses more tokens, money and time.

## Other observations

There are a few other things worth noting:

- Claude 3 Opus and Sonnet are both slower and more expensive than OpenAI's models. You can get almost the same coding skill faster and cheaper with OpenAI's models.
- Claude 3 has a 2X larger context window than the latest GPT-4 Turbo, which may be an advantage when working with larger code bases.
- The Claude models refused to perform a number of coding tasks and returned the error "Output blocked by content filtering policy". They refused to code up the [beer song](https://exercism.org/tracks/python/exercises/beer-song) program, which makes some sort of superficial sense. But they also refused to work in some larger open source code bases, for unclear reasons.
- The Claude APIs seem somewhat unstable, returning HTTP 5xx errors of various sorts. Aider automatically recovers from these errors with exponential backoff retries, but it's a sign that Anthropic made be struggling under surging demand.

