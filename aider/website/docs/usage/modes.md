---
parent: Usage
nav_order: 60
description: Using the code, architect, ask and help chat modes.
---

# Chat modes

Aider has a few different chat modes:

- `code` - Aider will make changes to your code to satisfy your requests.
- `ask` - Aider will discuss your code and answer questions about it, but never make changes.
- `architect` - Like code mode, aider will change your files. An architect model will propose changes and an editor model will translate that proposal into specific file edits.
- `help` - Aider will answer questions about aider: usage, configuration, troubleshooting, etc.

By default, aider starts in "code" mode. As you are talking, you can
send individual messages in a specific mode using 
`/code`, `/architect`, `/ask`, and `/help` commands:
Using these `/`-commands applies just to that particular message.
Your next message will go back to the active mode (usually "code" mode by default).

You can switch the active mode in a sticky way
with the `/chat-mode <mode>` command:

```
/chat-mode code
/chat-mode architect
/chat-mode ask
/chat-mode help
```

Or you can switch between coding modes using these commands without arguments:

```
/code
/architect
/ask
```

Or you can launch aider in one of the modes with the `--chat-mode <mode>` switch.
There is also a special shortcut `--architect` to launch in `--chat-mode architect`.

The aider prompt will indicate the active mode:

```
> This is code mode.
ask> This is ask mode.
architect> This is architect mode.
```


## Ask/code workflow

A recommended workflow is to bounce back and forth between `/ask` and `/code` modes.

Use ask mode to discuss what you want to do, get suggestions or options from aider
and provide feedback on the approach.
Once aider understands the mission, switch to code mode to have it start editing
your files.
All the conversation and decision making from ask mode will
help ensure that the correct code changes are performed.

You can be very terse when you finally switch from ask to code mode.
Saying something as simple as "go ahead" in code mode will
have aider execute on the plan you've been discussing.

Here's an example with two ask mode messages to agree on the plan, 
followed by two terse code mode messages to edit the code.

````
─────────────────────────────────────────────────────────────────────────────────────
Aider v0.79.0
Model: gemini/gemini-2.5-pro-exp-03-25 with diff-fenced edit format

> /ask What's the best thing to print if we're making a quick little demo program?

It sounds like you'd like to write a "Hello, world!" program. That's a very
popular phrase to use for small demo programs.

> /ask Yes, that's the idea. What are some more creative options?

1. "Greetings, Earthlings!"
2. "Beep boop, I am a computer!"
3. "To code, or not to code, that is the question."
4. "I think, therefore I print."
5. "01001000 01101001!" (Binary for "Hi!")

> do 4

hello.py
>>>>>>> SEARCH
=======
def main():
    print("I think, therefore I print.")
<<<<<<< REPLACE

> ALL CAPS!

hello.py
>>>>>>> SEARCH
    print("I think, therefore I print.")
=======
    print("I THINK, THEREFORE I PRINT!")
<<<<<<< REPLACE

````

You can think of this ask/code workflow as a more fluid version of
architect mode, but working just with one model the whole time.

## Architect mode and the editor model

When you are in architect mode, aider sends your requests to two models:

1. First, it sends your request to the main model which will act as an architect
to propose how to solve your coding request.
The main model is configured with `/model` or `--model`.

2. Aider then sends another request to an "editor model",
asking it to turn the architect's proposal into specific file editing instructions.
Aider has built in defaults to select an editor model based on your main model.
Or, you can choose a specific editor model with `--editor-model <model>`.

Certain LLMs aren't able to propose coding solutions *and*
specify detailed file edits all in one go.
For these models, architect mode can produce better results than code mode
by pairing them
with an editor model that is responsible for generating the file editing instructions.
But this uses two LLM requests,
which can take longer and increase costs.

Architect mode is especially useful with OpenAI's o1 models, which are strong at
reasoning but less capable at editing files.
Pairing an o1 architect with an editor model like GPT-4o or Sonnet will
give the best results.

But architect mode can also be helpful when you use the same model
as both the architect and the editor.
Allowing the model two requests to solve the problem and edit the files
can sometimes provide better results.

The editor model uses one of aider's edit formats to let the LLM
edit source files.
Aider will pick a suitable edit format by default,
but you can customize it with `--editor-edit-format <format>`.
The 
["editor-diff" and "editor-whole" edit formats](/docs/more/edit-formats.html#editor-diff-and-editor-whole)
are the recommended edit formats when using architect mode.
See this article on 
[aider's architect/editor mode](/2024/09/26/architect.html)
for more details.


## Examples

<div class="chat-transcript" markdown="1">


> Aider v0.47.1-dev  
> Models: claude-3-5-sonnet-20240620 with diff edit format  
> Git repo: .git with 298 files  
> Repo-map: using 1024 tokens  
> Use /help to see in-chat commands, run with --help to see cmd line args  

#### /ask What is this repo?

This is collection of python functions that compute various math functions.

#### /help How do I use aider with ollama?

Run `aider --model ollama/<ollama-model>`.
See these docs for more info: https://aider.chat/docs/llms/ollama.html

#### /code Add a function to calculate the factorial of a number

Certainly! I'll add a function to calculate the factorial of a number. Here's the change:

```python
def factorial(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)

# Example usage
print(factorial(5))  # Output: 120
```

This function uses recursion to calculate the factorial. It's been added to your code.

#### /architect Can we make this simpler?

Yes, you could replace the `factorial()` function with a call to the `math.factorial()`
builtin. 
This way you don't have to maintain a custom factorial implementation,
and the builtin function is well optimized.

```python
<<<<<<< SEARCH
def factorial(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)
=======
from math import factorial
>>>>>>> REPLACE
```

</div>

