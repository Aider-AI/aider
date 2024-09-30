---
parent: Usage
nav_order: 60
description: Using the chat, ask and help chat modes.
---

# Chat modes

Aider has a few different chat modes:

- `code` - Aider will make changes to your code to satisfy your requests.
- `architect` - Aider will first propose a solution, then ask if you want it to turn that proposal into edits to your files.
- `ask` - Aider will answer questions about your code, but never edit it.
- `help` - Aider will answer questions about using aider, configuring, troubleshooting, etc.

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

Or you can launch aider in one of the modes with the `--chat-mode <mode>` switch.
There is also a special shortcut `--architect` to launch in `--chat-mode architect`.

## Architect mode and the editor model

When you are in architect mode, aider sends your request to two models:

1. First, it sends your request to the main active model.
The main model is configured with `/model`, `--model` or the shortcut switches like `--sonnet`. 
After the main model replies, aider will offer to edit the files based on the response.

2. To edit the files, aider sends a second LLM request asking for specific code editing instructions.
This request goes to the "editor" model.
Aider has built in defaults to select an editor model based on your main model.
Or, you can choose an editor model yourself with `--editor-model <model>`.

Architect mode produces better results than code mode, but uses two LLM requests.
This probably makes it slower and more expensive than using code mode.

Architect mode is especially useful with OpenAI's o1 models, which are strong at
reasoning but less capable at editing files.
Pairing an o1 architect with an editor model like GPT-4o or Sonnet will
give the best results.

But architect mode is also quite helpful when you use GPT-4o or Sonnet
at both the architect and the editor.
Allowing the model two requests to solve the problem and edit the files
usually provides a better result.

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

This is the source code to the popular django package.

#### /help How do I use ollama?

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

> Edit the files? (Y)es/(N)o [Yes]: Yes

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

