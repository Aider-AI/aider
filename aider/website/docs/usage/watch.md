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

## AI comments

If you run aider with `--watch-files`, it will watch all files in your repo 
and look for any AI coding instructions you add using your favorite IDE or text editor.

Specifically, aider looks for one-liner comments (# ... or // ...) that either start or end with `AI` or `AI!`, like these:

```
# Implement a snake game. AI!
// Write self-learning protein folding prediction engine. AI!
```

Aider will take note of all the comments you add that start or end with `AI`, but
a comment that includes `AI!` with an exclamation point is special. 
That triggers aider to take action to collect *all* the AI comments and use them as instructions to make code changes.


## Example

For example, if you included this AI comment in your code:

```js
function factorial(n) // Implement this. AI!
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


Also see the demo video above that shows aider working with AI comments in VSCode. 

## Multiple uses



This capability is quite flexible and powerful once you get familiar with the various ways it can be used:

- Add an AI comment in the function you want changed, explaining the change request in-context right where you want the changes:
  - `# Add error handling here... AI!`
- Drop multiple `AI` comments without the `!` in multiple files, before triggering aider with a final `AI!`:
  - `# AI: Refactor this function...`
  - `# AI: Keep in mind the way it's used here.`
  - `# ... refactor it into a method here in this class. AI!`
- Just add `#AI` to a file and aider will automatically add it to the chat session. This is handy if you're looking at the file in your IDE and you want to add to the aider chat.

