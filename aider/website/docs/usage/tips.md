---
parent: Usage
nav_order: 25
description: Tips for AI pair programming with aider.
---

# Tips

- **Add just the files that need to be edited to the chat.**
Take a moment and think about which files will need to be changed.
Aider can often figure out which files to edit all by itself, but the most efficient approach is for you to add the files to the chat.
- **Don't add lots of files to the chat**, just the files you think need to be edited.
Too much irrelevant code will distract and confuse the LLM.
Aider uses a [map of your entire git repo](https://aider.chat/docs/repomap.html)
so is usually aware of relevant classes/functions/methods elsewhere in your code base.
It's ok to add 1-2 highly relevant files that don't need to be edited,
but be selective.
- **Break your goal down into bite sized steps.**
Do them one at a time. 
Adjust the files added to the chat as you go: `/drop` files that don't need any more changes, `/add` files that need changes for the next step.
- For more complex changes, use `/ask` to 
[discuss a plan first](modes.html).
Once you are happy with the approach, just say "go ahead" without the `/ask` prefix.
- Use Control-C to interrupt aider if it isn't providing a useful response. The partial response remains in the conversation, so you can refer to it when you reply with more information or direction.
- **If aider gets stuck** trying to make a change, try:
  - Using `/clear` to discard the chat history and make a fresh start.
  - Can you `/drop` any extra files?
  - Consider using `/ask` to discuss a plan before aider codes.
  - If aider is hopelessly stuck,
just code the next step yourself and try having aider code some more after that.
Pair program with aider.
- If your code is throwing an error, 
use the `/run` [in-chat command](commands.html)
to share the error output with the aider.
Or just paste the errors into the chat. Let the aider figure out and fix the bug.
- If test are failing, use the `/test` [in-chat command](commands.html)
to run tests and
share the error output with the aider.
- LLMs know about a lot of standard tools and libraries, but may get some of the fine details wrong about API versions and function arguments.
You can paste doc snippets into the chat or
include a URL to docs in your chat message.
Aider will scrape and read the URL.
- {% include multi-line.md %}

