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

// Write a self-learning protein folding prediction engine. AI!
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

This capability is quite flexible and powerful, and can be used in many ways.

### In-context instructions

You can add an AI comment in the function you want changed, 
explaining the change request in-context right where you want the changes.

```javascript
app.get('/sqrt/:n', (req, res) => {
    const n = parseFloat(req.params.n);

    // Add error handling for NaN and less than zero. AI!

    const result = math.sqrt(n);
    res.json({ result: result });
});
```

### Multiple comments

You can drop multiple `AI` comments without the `!`,
before triggering aider with a final `AI!`.
Also keep in mind that you can spread the AI comments across
multiple files, if you want to coordinate changes in multiple places.
Just use `AI!` last, to trigger aider.

```python
@app.route('/factorial/<int:n>')
def factorial(n):
    if n < 0:
        return jsonify(error="Factorial is not defined for negative numbers"), 400
        
    # AI: Refactor this code...
    
    result = 1
    for i in range(1, n + 1):
        result *= i
        
    # ... into to a compute_factorial() function. AI!
    
    return jsonify(result=result)
```

### Long form instructions

You can add a block of comments, with longer instructions.
Just be sure to start or end one of the lines with `AI` or `AI!` to draw
aider's attention to the block.

```python
# Make these changes: AI!
# - Add a proper main() function
# - Use Click to process cmd line args
# - Accept --host and --port args
# - Print a welcome message that includes the listening url

if __name__ == "__main__":
    app.run(debug=True)
```

### Add a file to the aider chat

Rather than using `/add` to add a file inside the aider chat, you can
simply put an `#AI` comment in it and save the file.
You can undo/remove the comment immediately if you like, the file
will still be added to the aider chat.

