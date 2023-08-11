
# Voice-to-code

Aider has experimental support for "voice-to-code",
allowing you to edit your codebase using spoken words.

You can speak to GPT to have it modify your code according to your
instructions.
Use the `/voice` in-chat command to start recording,
and press `ENTER` when you're done speaking.
Your voice coding instructions will be transcribed
and sent to GPT, as if you had manually typed them into
the aider chat session.

<div class="chat-transcript" markdown="1">

> Aider v0.11.2-dev  
> Added app.py to the chat.  

#### /voice  

<blockquote>
<p>Recording, press ENTER when done... 3.5sec 
<div id="progress-bar">
    <div id="progress"></div>
</div>
</p>
</blockquote>

<style>
    #progress-bar {
        width: 100px;
        height: 20px;
        background-color: #f0f0f0;
        border-radius: 10px;
    }
    #progress {
        height: 100%;
        background-color: #333;
        animation: progress 1s infinite;
    }
    @keyframes progress {
        0% { width: 10%; }
        50% { width: 90%; }
        100% { width: 10%; }
    }
</style>

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
