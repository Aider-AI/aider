# Code editing benchmarks for OpenAI's "1106" models

[![benchmark results](../assets/benchmarks-1106.svg)](https://aider.chat/assets/benchmarks-1106.svg)

[OpenAI just released new versions of GPT-3.5 and GPT-4](https://openai.com/blog/new-models-and-developer-products-announced-at-devday),
and there's a lot
of interest about their ability to code compared to the previous versions.
With that in mind, I've been benchmarking the new models.

Aider is an open source command line chat tool that lets you work with GPT to edit
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

The benchmark users aider to try and complete
[133 Exercism Python coding exercises](https://github.com/exercism/python).
For each exercise, Exercism provides a starting python file with stubs for the needed functions,
a natural language description of the problem to solve
and a test suite to evaluate whether the coder has correctly solved the problem.

The benchmark gives aider two tries to complete the task:

1. On the first try, aider gives GPT the stub code file to edit and the natural language instructions that describe the problem.
2. If the test suite fails after the first try, aider gives GPT the test error output and asks it to fix the code. Aider supports this sort of interaction when chatting with GPT using a command like `/run pytest` to run and share pytest results in the chat with GPT. You can `/run` whatever tests/linters/etc make sense for your language/framework/situation.

## Benchmark results on the new "1106" models

### gpt-4-1106-preview

- The new `gpt-4-1106-preview` model seems **much faster** than the earlier GPT-4 models! I won't be able to properly quantify this until the rate limits loosen up. Currently I am seeing 10X faster responses.
- **It is much better at producing correct code on the first try**. It gets ~60% of the coding exercises correct, without needing to see errors from the test suite. Previous models only get 46-47% of the exercises correct on the first try.
- The new model seems to perform somewhat better (69%) than the old models (63-64%) after being given a second chance to correct bugs by reviewing test suite error output.

**These results are preliminiary.**
OpenAI is enforcing very low
rate limits on the new GPT-4 model. The limits are so low, that
I have only been able to attempt
58
out of 133 exercism problems.
The problems are selected in random order, so results should be *roughly*
indicative of the full benchmark.

### gpt-3.5-turbo-1106

- The new `gpt-3.5-turbo-1106` model is completing the benchmark **3-4X faster** than the earlier GPT-3.5 models.
- The success rate after the first try of 42% is comparable to the previous June (0613) model. The new November and previous June models are both worse than the original March (0301) model's 50% result on the first try.
- The new model's 56% success rate after the second try seems comparable to the original March model, and somewhat better than the June model's 50% score.


### Updates

I will update the results on this page as quickly my rate limit allows.
