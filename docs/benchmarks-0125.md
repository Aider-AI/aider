# Lazy coding benchmark for gpt-4-0125-preview

[![benchmark results](../assets/benchmarks-0125.svg)](https://aider.chat/assets/benchmarks-0125.svg)

[OpenAI just released a new version of GPT-4 Turbo](https://openai.com/blog/new-embedding-models-and-api-updates).
This new model is intended to reduce the "laziness" that has been widely observed with the previous `gpt-4-1106-preview` model:

> Today, we are releasing an updated GPT-4 Turbo preview model, gpt-4-0125-preview. This model completes tasks like code generation more thoroughly than the previous preview model and is intended to reduce cases of “laziness” where the model doesn’t complete a task.

With that in mind, I've been benchmarking the new model using
aider's existing
[lazy coding benchmark](https://aider.chat/docs/unified-diffs.html).

## Benchmark results

Overall,
the new `gpt-4-0125-preview` model seems lazier
than the November `gpt-4-1106-preview` model:

- It gets worse benchmark scores when using the [unified diffs](https://aider.chat/docs/unified-diffs.html) code editing format.
- Using aider's older [SEARCH/REPLACE block](https://github.com/paul-gauthier/aider/blob/9033be74bf74ae70459013e54b2ae6a97c47c2e6/aider/coders/editblock_prompts.py#L75-L80) editing format, the new January model outperforms the older November model. But it still performs worse than both models using unified diffs.

## Related reports

This is one in a series of reports
that use the aider benchmarking suite to assess and compare the code
editing capabilities of OpenAI's GPT models.
You can review the other reports
for additional information:

- [GPT code editing benchmarks](https://aider.chat/docs/benchmarks.html) evaluates the March and June versions of GPT-3.5 and GPT-4.
- [Code editing benchmarks for OpenAI's "1106" models](https://aider.chat/docs/benchmarks-1106.html).
- [Aider's lazy coding benchmark](https://aider.chat/docs/unified-diffs.html).


