---
parent: Troubleshooting
nav_order: 10
---

# File editing problems

Sometimes the LLM will reply with some code changes
that don't get applied to your local files.
In these cases, aider might say something like "Failed to apply edit to *filename*"
or other error messages.

This usually happens because the LLM is disobeying the system prompts
and trying to make edits in a format that aider doesn't expect.
Aider makes every effort to get the LLM
to conform, and works hard to deal with
LLM edits that are "almost" correctly formatted.

But sometimes the LLM just won't cooperate.
In these cases, here are some things you might try.

## Don't add too many files

Many LLMs now have very large context windows,
but filling them with irrelevant code or conversation 
can confuse the model.
Above about 25k tokens of context, most models start to become distracted and become less likely
to conform to their system prompt.

- Don't add too many files to the chat, *just* add the files you think need to be edited.
Aider also sends the LLM a [map of your entire git repo](https://aider.chat/docs/repomap.html), so other relevant code will be included automatically.
- Use `/drop` to remove files from the chat session which aren't needed for the task at hand. This will reduce distractions and may help the LLM produce properly formatted edits.
- Use `/clear` to remove the conversation history, again to help the LLM focus.
- Use `/tokens` to see how many tokens you are using for each message.

## Use a more capable model

If possible try using GPT-4o, o3-mini, Claude 3.7 Sonnet, DeepSeek V3 or DeepSeek R1.
They are the strong and capable models.

Weaker models
are more prone to
disobeying the system prompt instructions.
Most local models are just barely capable of working with aider,
so editing errors are probably unavoidable.

## Local models: context window and quantization

Be especially careful about the
[Ollama context window](https://aider.chat/docs/llms/ollama.html#setting-the-context-window-size)
when working with local models.
It defaults to be very small and silently discards data if you exceed it.

Local models which have been quantized are more likely to have editing problems
because they are not capable enough to follow aider's system prompts.

## Try the whole edit format

Run aider with `--edit-format whole` if were using a different edit format.
You can see which edit format it is using in the announce lines:

```
Aider v0.50.2-dev
Models: claude-3-5-sonnet-20240620 with ♾️ diff edit format
```

## Try architect mode

Run aider with `--architect` or `/chat-mode architect` to enable [architect mode](../usage/modes.md#architect-mode-and-the-editor-model).
This mode first proposes changes, then uses a separate model to handle the file edits.
This two-step process often produces more reliable edits, especially with models that have trouble
following edit format instructions.

## More help

{% include help.md %}
