---
title: Aider in your IDE
#highlight_image: /assets/browser.jpg
parent: Usage
nav_order: 750
description: Aider can run in your browser, not just on the command line.
---

# Aider in your IDE

<video width="100%" controls>
  <source src="/assets/videos/aider-watch-demo.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

If you run aider with `--watch-files`,
it will watch all files in your repo for edits. If you edit a file and add comments with "AI instructions", aider will follow them. So you can put aider messages right into your source files, nearby the code they refer to. 


Specifically, aider will react to one-liner comments (# ... or // ...) that either start or end with `AI` or `AI!`. 

Comments that use `AI!` with an exclamation point are special. They trigger aider to take action to process all the AI comments and use them as instructions to make code changes.

For example, if you included this AI comment in your code:

```js
function factorial(n)
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

This makes it easier to use aider from within your favorite editor or IDE. 
See the demo video above of aider working with AI comments in VSCode.

This capability is quite flexible and powerful once you get familiar with the various ways it can be used:

- Just add #AI to a file to add it to the chat.
- Add an AI comment in the function you want changed, explaining the change request in-context.
  - `# Add error handling... AI!`
- Drop multiple AI comments (in multiple files) before triggering aider with a final AI!:
  - `# AI: Refactor this function...`
  - `# ... into a method here in this class. AI!`

