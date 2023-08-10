
# Voice-to-code

Aider has experimental support for "voice-to-code",
allowing you to edit your codebase using spoken words.

You can speak to GPT to have it modify your code according to your
instructions.
Use the `/voice` in-chat command to start recording,
and press `ENTER` when you're done speaking.
Your voice coding instrucitons will be transcribed
and sent to GPT, as if you had manually typed them into
the aider chat session.

<br/>
<br/>
<br/>
<div class="chat-transcript" markdown="1">

> Aider v0.11.2-dev  
> Model: gpt-4  
> Git repo: .git  
> Repo-map: universal-ctags using 1024 tokens  
> Added app.py to the chat.  
> Use /help to see in-chat commands, run with --help to see cmd line args  

#### /voice  

> Recording... Press ENTER when done speaking...  

<div style="display: inline-block; position: relative; width: 200px; background-color: #f0f0f0; border-radius: 10px; padding: 10px; color: #333; font-family: 'Comic Sans MS', cursive, sans-serif;">
<span style="position: absolute; top: 0; left: 50%; transform: translate(-50%, -100%); width: 0; height: 0; border-left: 10px solid transparent; border-right: 10px solid transparent; border-bottom: 10px solid #f0f0f0;"></span>
“add a factorial endpoit that uses math factorial”
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
