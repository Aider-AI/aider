---
title: Code editing benchmarks for OpenAI's "1106" models
excerpt: A quantitative comparison of the code editing capabilities of the new GPT-3.5 and GPT-4 versions that were released in Nov 2023.
highlight_image: /assets/benchmarks-1106.jpg
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Code editing benchmarks for OpenAI's "1106" models

[![benchmark results](/assets/benchmarks-1106.svg)](https://aider.chat/assets/benchmarks-1106.svg)

[![benchmark results](/assets/benchmarks-speed-1106.svg)](https://aider.chat/assets/benchmarks-speed-1106.svg)

[OpenAI just released new versions of GPT-3.5 and GPT-4](https://openai.com/blog/new-models-and-developer-products-announced-at-devday),
and there's a lot
of interest about their ability to code compared to the previous versions.
With that in mind, I've been benchmarking the new models.

[Aider](https://github.com/Aider-AI/aider)
is an open source command line chat tool that lets you work with GPT to edit
code in your local git repo.
To do this, aider needs to be able to reliably recognize when GPT wants to edit
your source code,
determine which files it wants to modify
and accurately apply the changes it's trying to make.
Doing a good job on this "code editing" task requires a good LLM, good prompting and
a good tool driving the interactions with the LLM.

Aider relies on a
[code editing benchmark](https://aider.chat/docs/benchmarks.html)
to quantitatively evaluate
performance
whenever one of these things changes.
For example,
whenever I change aider's prompting or the backend which drives LLM conversations,
I run the benchmark to make sure these changes produce improvements (not regressions).

The benchmark uses aider to try and complete
[133 Exercism Python coding exercises](https://github.com/exercism/python).
For each exercise, Exercism provides a starting python file with stubs for the needed functions,
a natural language description of the problem to solve
and a test suite to evaluate whether the coder has correctly solved the problem.

The benchmark gives aider two tries to complete the task:

1. On the first try, aider gives GPT the stub code file to edit and the natural language instructions that describe the problem. This reflects how you code with aider. You add your source code files to the chat and ask for changes, which are automatically applied.
2. If the test suite fails after the first try, aider gives GPT the test error output and asks it to fix the code. Aider supports this sort of interaction using a command like `/run pytest` to run and share pytest results in the chat with GPT. You can `/run` whatever tests/linters/etc make sense for your language/framework/situation.

## Benchmark results

### gpt-4-1106-preview

For now, I have only benchmarked the GPT-4 models using the `diff` edit method.
This is the edit format that aider uses by default with gpt-4.

- The new `gpt-4-1106-preview` model seems **2-2.5X faster** than the June GPT-4 model.
- **It seems better at producing correct code on the first try**. It gets
53% of the coding exercises correct, without needing to see errors from the test suite. Previous models only get 46-47% of the exercises correct on the first try.
- The new model seems to perform similar
(~65%) to the old models (63-64%) after their second chance to correct bugs by reviewing test suite error output.

### gpt-3.5-turbo-1106

I benchmarked the GPT-3.5 models with both the `whole` and `diff` edit format.
None of the gpt-3.5 models seem able to effectively use the `diff` edit format, including the newest November (1106) model.

The comments below only focus on comparing the `whole` edit format results:

- The new `gpt-3.5-turbo-1106` model is completing the benchmark **3-4X faster** than the earlier GPT-3.5 models.
- The success rate after the first try of 42% is comparable to the previous June (0613) model. The new November and previous June models are both worse than the original March (0301) model's 50% result on the first try.
- The new model's 56% success rate after the second try seems comparable to the original March model, and somewhat better than the June model's 50% score.


## Related reports

This is one in a series of reports
that use the aider benchmarking suite to assess and compare the code
editing capabilities of OpenAI's GPT models.
You can review the other reports
for additional information:

- [GPT code editing benchmarks](https://aider.chat/docs/benchmarks.html) evaluates the March and June versions of GPT-3.5 and GPT-4.
- [Code editing speed benchmarks for OpenAI's "1106" models](https://aider.chat/2023/11/06/benchmarks-speed-1106.html) compares the performance of the new GPT models.


## Updates

Last updated 11/14/23.
OpenAI has relaxed rate limits so these results are no longer considered preliminary.
