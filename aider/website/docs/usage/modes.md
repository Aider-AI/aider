---
parent: Usage
nav_order: 60
description: Using the chat, ask and help chat modes.
---

# Chat modes

Aider has 3 different chat modes:

- `code` - Aider will make changes to your code to satisfy your requests.
- `ask` - Aider will answer questions about your code, but never edit it.
- `help` - Aider will answer questions about using aider, configuring, troubleshooting, etc.

By default, aider starts in "code" mode. As you are talking, you can
send individual messages in a specific mode using `/code`, `/ask`, and `/help` commands:
Using `/code`, `/ask`, and `/help` applies just to that particular message.
Your next message will go back to the active mode (usually "code" mode by default).

You can switch the active mode in a sticky way
with the `/chat-mode <mode>` command:

```
/chat-mode code
/chat-mode ask
/chat-mode help
```

Or you can launch aider in one of the modes with the `--chat-mode <mode>` switch.

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

</div>

