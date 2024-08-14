---
title: LLMs are bad at returning code in json
excerpt: LLMs write worse code if you ask them to return the code wrapped in json via a tool/function call.
highlight_image: /assets/code-in-json.jpg
draft: true
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# LLMs are bad at returning code in json


A lot of people wonder why aider doesn't have LLMs use tools or function calls to
specify code edits.
Instead, aider asks LLMs to return code edits in plain text, like this:

````
greeting.py
```python
<<<<<<< SEARCH
def greeting():
    print("Hello")
=======
def greeting():
    print("Goodbye")
>>>>>>> REPLACE
```
````

People expect that it would be easier and more reliable
for aider to parse a nicely formatted json 
response more like this:

```
{
    "filename": "greeting.py",
    "start_line": 6,
    "end_line": 7,
    "new_content": "def greeting():\n    print(\"Goodbye\")\n"
}
```

This seems even more tempting as LLMs get better tooling for reliably generating
valid json, or even enforcing that it meets a specific schema.
For example, OpenAI recently announced
[strict enforcement of json responses]().

The problem is that LLMs are bad a writing code when you ask them to wrap it
into a json container.
The json tooling around the LLM helps make sure it's valid json,
which does solve an important problem. 
LLMs used to frequently produce invalid json, so that's a big step forward.

The problem remains, LLMs write worse code when they're asked to 
emit it wrapped in json.
In some sense this shouldn't be surprising.
Just look at the very simple
json example above, with the escaped 
quotes `\"` quotes
newlines `\n`
mixed into the code.
Coding is complicated enough without having to escape all the special characters too.

If I asked you to write me a program, would you do a better job
typing it into a text file or hand typing it as a properly escaped json string?

## Quantifying the benefits of plain text


Previous [benchmark results](/2023/07/02/benchmarks.html)
showed
the superiority of plain text coding compared to json-wrapped function calls,
but they were done over a year ago.
OpenAI's newly announced support for "strict" json seemed like a good reason to
investigate whether the newest models are still handicapped by json-wrapping code.

To find out, I benchmarked 3 of the strongest code editing models:

- gpt-4o-2024-08-06
- claude-3-5-sonnet-20240620
- deepseek-coder (V2 0724)

Each model was given one try to solve 
[133 practice exercises from the Exercism python repository](/2023/07/02/benchmarks.html#the-benchmark).
This is the standard aider "code editing" benchmark, except restricted to a single attempt.

Each model ran through the benchmark with two strategies for returning code:

- **Markdown** -- where the model simply returns the whole source code file in standard markdown triple-backtick fences.
- **Tool call** -- where the model is told to use a function to return the whole source code file. This requires the LLM to wrap the code in json.

The markdown strategy would return a program like this:

````
Here is the program you asked for which prints "Hello, world!":

greeting.py
```
def greeting():
    print("Hello")
```
````

The tool strategy requires the LLM to call the `write_file` function with
two parameters, like this:

```
{
    "explanation": "Here is the program you asked for which prints \"Hello, world!\"",
    "content": "def greeting():\n    print(\"Hello\")\n"
}
```

Both of these formats avoid actually *editing* source files, to keep things as
simple as possible.
This makes the task much easier, since the LLM can emit the whole source file intact.
LLMs find it much more challenging to correctly formulate instructions to edit
portions of a file.

We are simply testing the effects of json-wrapping on the LLMs ability to solve coding tasks.

## Results

All 3 models did significantly worse on the benchmark when asked to
return json-wrapped code in a tool function call.
