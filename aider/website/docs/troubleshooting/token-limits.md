---
parent: Troubleshooting
nav_order: 25
---

# Token limits

Every LLM has limits on how many tokens it can process for each request:

- The model's **context window** limits how many total tokens of
*input and output* it can process.
- Each model has limit on how many **output tokens** it can
produce.

Aider will report an error if a model responds indicating that
it has exceeded a token limit.
The error will include suggested actions to try and
avoid hitting token limits.
Here's an example error:

```
Model gpt-3.5-turbo has hit a token limit!

Input tokens: 768 of 16385
Output tokens: 4096 of 4096 -- exceeded output limit!
Total tokens: 4864 of 16385

To reduce output tokens:
- Ask for smaller changes in each request.
- Break your code into smaller source files.
- Try using a stronger model like gpt-4o or opus that can return diffs.

For more info: https://aider.chat/docs/token-limits.html
```

## Input tokens & context window size

The most common problem is trying to send too much data to a 
model,
overflowing its context window.
Technically you can exhaust the context window if the input is
too large or if the input plus output are too large.

Strong models like GPT-4o and Opus have quite
large context windows, so this sort of error is
typically only an issue when working with weaker models.

The easiest solution is to try and reduce the input tokens
by removing files from the chat.
It's best to only add the files that aider will need to *edit*
to complete your request.

- Use `/tokens` to see token usage.
- Use `/drop` to remove unneeded files from the chat session.
- Use `/clear` to clear the chat history.
- Break your code into smaller source files.

## Output token limits

Most models have quite small output limits, often as low
as 4k tokens.
If you ask aider to make a large change that affects a lot
of code, the LLM may hit output token limits
as it tries to send back all the changes.

To avoid hitting output token limits:

- Ask for smaller changes in each request.
- Break your code into smaller source files.
- Use a strong model like gpt-4o, sonnet or opus that can return diffs.
- Use a model that supports [infinite output](/docs/more/infinite-output.html).

## Other causes

Sometimes token limit errors are caused by 
non-compliant API proxy servers
or bugs in the API server you are using to host a local model.
Aider has been well tested when directly connecting to 
major 
[LLM provider cloud APIs](https://aider.chat/docs/llms.html).
For serving local models, 
[Ollama](https://aider.chat/docs/llms/ollama.html) is known to work well with aider.

Try using aider without an API proxy server
or directly with one of the recommended cloud APIs
and see if your token limit problems resolve.

## More help

{% include help.md %}
