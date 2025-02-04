# flake8: noqa: E501

from .editblock_prompts import EditBlockPrompts


class EditBlockFencedPrompts(EditBlockPrompts):
    example_messages = [
        dict(
            role="user",
            content="Change get_factorial() to use math.factorial",
        ),
        dict(
            role="assistant",
            content="""To make this change we need to modify `mathweb/flask/app.py` to:

1. Import the math package.
2. Remove the existing factorial() function.
3. Update get_factorial() to call math.factorial instead.

Here are the *SEARCH/REPLACE* blocks:

{fence[0]}
mathweb/flask/app.py
{search_divider}
from flask import Flask
{middle_divider}
import math
from flask import Flask
{replace_divider}
{fence[1]}

{fence[0]}
mathweb/flask/app.py
{search_divider}
def factorial(n):
    "compute factorial"

    if n == 0:
        return 1
    else:
        return n * factorial(n-1)

{middle_divider}
{replace_divider}
{fence[1]}

{fence[0]}
mathweb/flask/app.py
{search_divider}
    return str(factorial(n))
{middle_divider}
    return str(math.factorial(n))
{replace_divider}
{fence[1]}
<<<<<<< HEAD
""",
        ),
        dict(
            role="user",
            content="Refactor hello() into its own file.",
        ),
        dict(
            role="assistant",
            content="""To make this change we need to modify `main.py` and make a new file `hello.py`:

1. Make a new hello.py file with hello() in it.
2. Remove hello() from main.py and replace it with an import.

Here are the *SEARCH/REPLACE* blocks:

{fence[0]}
hello.py
{search_divider}
{middle_divider}
def hello():
    "print a greeting"

    print("hello")
{replace_divider}
{fence[1]}

{fence[0]}
main.py
{search_divider}
def hello():
    "print a greeting"

    print("hello")
{middle_divider}
from hello import hello
{replace_divider}
{fence[1]}
""",
        ),
    ]
