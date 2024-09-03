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

## Use a capable model

If possible try using GPT-4o, Claude 3.5 Sonnet or Claude 3 Opus, 
as they are the strongest and most capable models.

Weaker models
are more prone to
disobeying the system prompt instructions.
Most local models are just barely capable of working with aider,
so editing errors are probably unavoidable.

Local models which have been quantized are even more likely to have problems
because they are not capable enough to follow aider's system prompts.

## Try the whole format

Run aider with `--edit-format whole` if the model is using a different edit format.
You can see which edit format it is using in the announce lines:

```
Aider v0.50.2-dev
Models: claude-3-5-sonnet-20240620 with ♾️ diff edit format
```

## Reduce distractions

Many LLMs now have very large context windows,
but filling them with irrelevant code or conversation 
can confuse the model.

- Don't add too many files to the chat, *just* add the files you think need to be edited.
Aider also sends the LLM a [map of your entire git repo](https://aider.chat/docs/repomap.html), so other relevant code will be included automatically.
- Use `/drop` to remove files from the chat session which aren't needed for the task at hand. This will reduce distractions and may help the LLM produce properly formatted edits.
- Use `/clear` to remove the conversation history, again to help the LLM focus.
- Use `/tokens` to see how many tokens you are using for each message.

## More help

{% include help.md %}
