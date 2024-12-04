---
title: Aider in your IDE
#highlight_image: /assets/browser.jpg
parent: Usage
nav_order: 750
description: Aider can run in your browser, not just on the command line.
---

# Aider in your IDE

<div class="video-container">
  <video controls loop poster="/assets/watch.jpg">
    <source src="/assets/watch.mp4" type="video/mp4">
    <a href="/assets/watch.mp4">Aider browser UI demo video</a>
  </video>
</div>

<style>
.video-container {
  position: relative;
  padding-bottom: 101.89%; /* 1080 / 1060 = 1.0189 */
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

If you run aider with `--watch-files`, it will watch all files in your repo for
any instructions you add using your favorite IDE or text editor.
If you add code comments with "AI instructions", aider will follow them.
So you can put aider instructions right into your source files using your IDE.

Specifically, aider will react to one-liner comments (# ... or // ...) that either start or end with `AI` or `AI!`. 

Comments that use `AI!` with an exclamation point are special. They trigger aider to take action to process all the AI comments and use them as instructions to make code changes.

For example, if you included this AI comment in your code:

```js
function factorial(n) {
// Implement this. AI!
```

Then aider would update the file and implement the function:

```js
function factorial(n) {
  if (n === 0 || n === 1) {
    return 1;
  } else {
    return n * factorial(n - 1);
  }
}
```

This makes it easier to use aider with your favorite editor or IDE. 
See the demo video above that shows aider working with AI comments in VSCode. 

This capability is quite flexible and powerful once you get familiar with the various ways it can be used:

- Add an AI comment in the function you want changed, explaining the change request in-context right where you want the changes:
  - `# Add error handling... AI!`
- Drop multiple AI comments (in multiple files) before triggering aider with a final `AI!`:
  - `# AI: Refactor this function...`
  - `# ... into a method here in this class. AI!`
- Just add `#AI` to a file and aider will automatically add it to the chat session.
