---
title: Copy/paste with web chat
#highlight_image: /assets/browser.jpg
parent: Usage
nav_order: 850
description: Aider works with LLM web chat UIs
---

# Copy/paste with web chat

<div class="video-container">
  <video controls loop poster="/assets/copypaste.jpg">
    <source src="/assets/copypaste.mp4" type="video/mp4">
    <a href="/assets/copypaste.mp4">Aider browser UI demo video</a>
  </video>
</div>

<style>
.video-container {
  position: relative;
  padding-bottom: 66.34%; /* 2160 / 3256 = 0.6634 */
  height: 0;
  overflow: hidden;
}

.video-container video {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}
</style>

## Working with an LLM web chat

[Aider can connect to most LLMs via API](https://aider.chat/docs/llms.html) and works best that way.
But there are times when you may want to work with an LLM via its web chat interface:

- Workplace policies may limit your LLM usage to a proprietary web chat system.
- The web chat LLM may have access to unique context or may have been specially fine tuned for your task.
- It may be cost prohibitive to use some models via API.
- There may not be an API available.

Aider has features for working with an LLM via its web chat interface.
This allows you to use the web chat LLM as the "big brain code architect"
while running aider with a smaller, cheaper LLM to actually make changes
to your local files.

For this "file editor" part of the process 
you can run aider with many open source, free or very inexpensive LLMs.
For example, the demo video above shows aider using DeepSeek to apply the changes
that o1-preview is suggesting in the web chat.

### Copy aider's code context to your clipboard, paste into the web UI

The `/copy-context <instructions>` command can be used in chat to copy aider's code context to your clipboard.
It will include:

- All the files which have been added to the chat via `/add`.
- Any read only files which have been added via `/read`.
- Aider's [repository map](https://aider.chat/docs/repomap.html) that brings in code context related to the above files from elsewhere in your git repo.
- Some instructions to the LLM that ask it to output change instructions concisely.
- If you include `<instructions>`, they will be copied too.

You can paste the context into your browser, and start interacting with the LLM web chat to
ask for code changes.

### Paste the LLM's reply back into aider to edit your files

Once the LLM has replied, you can use the "copy response" button in the web UI to copy
the LLM's response.
Back in aider, you can run `/paste` and aider will edit your files
to implement the changes suggested by the LLM.

You can use a cheap, efficient model like GPT-4o Mini, DeepSeek or Qwen to do these edits.
This works best if you run aider with `--edit-format editor-diff` or `--edit-format editor-whole`.

### Copy/paste mode

Aider has a `--copy-paste` mode that streamlines this entire process:

- Whenever you `/add` or `/read` files, aider will automatically copy the entire, updated
code context to your clipboard. 
You'll see "Copied code context to clipboard" whenever this happens.
- When you copy the LLM reply to your clipboard outside aider, aider will automatically notice
and load it into the aider chat. 
Just press ENTER to send the message
and aider will apply the LLMs changes to your local files.
- Aider will automatically select the best edit format for this copy/paste functionality. 
Depending on the LLM you have aider use, it will be either `editor-whole` or `editor-diff`.

## Terms of service

Be sure to review the Terms Of Service of any LLM web chat service you use with
these features.
These features are not intended to be used in violation of any service's Terms Of Service (TOS).

Aider's web chat features have been designed to be compliant with the 
terms of service of most LLM web chats.

There are 4 copy/paste steps involved when coding with an LLM web chat:

1. Copy code and context from aider.
2. Paste the code and context into the LLM web chat.
3. Copy the reply from the LLM web chat.
4. Paste the LLM reply into aider.

Most LLM web chat TOS prohibit automating steps (2) and (3) where code
is copied from and pasted into the web chat.
Aider's `--copy-paste` mode leaves those as 100% manual steps for the user to complete.
It simply streamlines steps (1) and (4) that are interactions with aider,
and which should not be under the scope of an LLM web chat TOS.

If you are concerned that
the automatic interactions with aider in steps (1) and (4) may be problematic with respect to
your LLM web chat provider's TOS, you can forego `--copy-paste` mode.
Instead, manually use the `/copy-context` and `/paste` commands if that
will keep you in compliance.

Again, do not use these features in violation of any service's Terms Of Service.
