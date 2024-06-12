---
parent: Usage
nav_order: 100
description: Speak with aider about your code!
---

# Voice-to-code with aider

Speak with aider about your code! Request new features, test cases or bug fixes using your voice and let aider do the work of editing the files in your local git repo. As with all of aider's capabilities, you can use voice-to-code with an existing repo or to start a new project.

Voice support fits quite naturally into aider's AI pair programming
chat interface. Now you can fluidly switch between voice and text chat
when you ask aider to edit your code.

## How to use voice-to-code

Use the in-chat `/voice` command to start recording,
and press `ENTER` when you're done speaking.
Your voice coding instructions will be transcribed, 
as if you had  typed them into
the aider chat session.

See the [installation instructions](https://aider.chat/docs/install/optional.html#enable-voice-coding) for
information on how to enable the `/voice` command.

<br/>
<div class="chat-transcript" markdown="1">

> Aider v0.11.2-dev  
> Added app.py to the chat.  

#### /voice

<blockquote>
<div class="recording-line">
    <p style="display: inline;">Recording, press ENTER when done... <span id="timer">3.5</span>sec</p>
    <div id="progress-bar">
        <div id="progress"></div>
    </div>
</div>
</blockquote>

<style>
    .recording-line > * {
        display: inline-block;
        vertical-align: middle;
    }
    #progress-bar {
        width: 100px;
        height: 20px;
        background-color: #333;
        margin-left: 10px;
    }
    #progress {
        height: 100%;
        background-color: #f0f0f0;
        animation: progress 3s infinite;
    }
    @keyframes progress {
        0% { width: 10%; }
        20% { width: 90%; }
        50% { width: 30%; }
        60% { width: 90%; }
        80% { width: 20%; }
        100% { width: 10%; }

    }
</style>

<script>
window.onload = function() {
    var counter = 0;
    var timer = document.getElementById('timer');
    setInterval(function() {
        counter = (counter + 0.1) % 9;
        timer.textContent = counter.toFixed(1);
    }, 100);
}
</script>

<div style="display: inline-block; position: relative; width: 200px; background-color: #f0f0f0; border-radius: 10px; padding: 10px; color: #333; font-family: 'Comic Sans MS', 'Comic Sans', 'Marker Felt', sans-serif;">
<span style="position: absolute; top: 0; left: 50%; transform: translate(-50%, -100%); width: 0; height: 0; border-left: 10px solid transparent; border-right: 10px solid transparent; border-bottom: 10px solid #f0f0f0;"></span>
“&nbsp;add a factorial endpoint that uses math factorial&nbsp;”
</div>

#### Add a factorial endpoint that uses math.factorial.

To add a factorial endpoint to the Flask application, we need to modify the `app.py` file.

Here are the steps:

1. Add a new route `/fact/<int:x>` to the Flask application.
2. In the function for this route, call `math.factorial(x)` and return the result as a string.

Here is the *edit block* for these changes:

```python
app.py
<<<<<<< HEAD
if __name__ == '__main__':
    print("Starting...")
    app.run()
=======
@app.route('/fact/<int:x>')
def factorial(x):
    result = math.factorial(x)
    return str(result)

if __name__ == '__main__':
    print("Starting...")
    app.run()
>>>>>>> updated
```

> Applied edit to app.py  
> Commit ef9e3e7 aider: Add a factorial endpoint that uses math.factorial.  

</div>
<br/>
<br/>
<br/>
