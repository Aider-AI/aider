---
title: LLMs are bad at returning code in JSON
excerpt: LLMs write worse code if you ask them to return the code wrapped in JSON (via a tool or function call).
highlight_image: /assets/code-in-json.jpg
draft: true
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# LLMs are bad at returning code in JSON


## Abstract

Current LLMs have support for returning properly formatted JSON,
making it easier for clients to reliably parse complex responses.
It therefore seems attractive for
AI coding applications ask LLMs to return code in structured JSON replies.
Unfortunately, 
LLMs write worse code when asked to wrap it in JSON, harming their ability
to correctly solve coding tasks.
On a variant of the aider code editing benchmark, 
asking for JSON-wrapped code
often significantly harms coding
performance.
This holds true across many top coding LLMs, 
including OpenAI's latest model gpt-4o-2024-08-06 
which has strong JSON support.

{% include code-in-json-benchmark.js %}

> Figure 1: Benchmark scores of models using either plain markdown text or JSON to return code,
> averaged over 5 runs.
> Models produce better code when they return it as plain markdown text, as compared to wrapping it in JSON for a tool function call.


## Introduction

A lot of people wonder why aider doesn't use LLM tools for code editing.
Instead, aider asks for code edits in plain text, like this:

````
greeting.py
```
<<<<<<< SEARCH
def greeting():
    print("Hello")
=======
def greeting():
    print("Goodbye")
>>>>>>> REPLACE
```
````

People expect that it would be easier and more reliable to use tool calls,
which would return a structured JSON response:

```json
{
    "filename": "greeting.py",
    "search": "def greeting():\n    print(\"Hello\")\n"
    "replace": "def greeting():\n    print(\"Goodbye\")\n"
}
```

This has become even more tempting as LLM providers
continue to improve their tooling for reliably generating
valid JSON.
For example, OpenAI recently announced the ability to
[strictly enforce that JSON responses will be syntactically correct 
and conform to a specified schema](https://openai.com/index/introducing-structured-outputs-in-the-api/).

But producing valid (schema compliant) JSON is not sufficient for working with AI generated code.
The code inside the JSON has to be valid and high quality too.
Unfortunately, 
LLMs write worse code when they're asked to 
wrap it in JSON.

In some sense this shouldn't be surprising.
Just look at the very simple
JSON example above, with the escaped 
quotes `\"` and
newlines `\n`
mixed into the code.
Imagine the additional
complexity
if the code itself contained quoted strings
with their
own escape sequences.

Would *you* write better code by
typing it out normally
or as a properly escaped 
JSON string?


## Quantifying the benefits of plain text

Previous [aider benchmark results](/2023/07/02/benchmarks.html)
showed
the superiority of returning code
as plain text compared to JSON-wrapped function calls.
Those results were obtained
over a year ago, against far less
capable models.
OpenAI's newly announced support for "strict" JSON seemed like a good reason to
investigate whether the newest models are still handicapped by JSON-wrapping code.

Four of the strongest code editing models were benchmarked
to assess the impact of JSON-wrapping code:

- claude-3-5-sonnet-20240620
- deepseek-coder (V2 0724)
- gpt-4o-2024-05-13
- gpt-4o-2024-08-06

Each model was given one try to solve 
[133 practice exercises from the Exercism python repository](/2023/07/02/benchmarks.html#the-benchmark).
This is the standard aider "code editing" benchmark, but restricted to a single attempt
without a second try to "fix" any errors.

The benchmark assessed the models coding ability
using different strategies for returning code:

- **Markdown** -- the model returned the whole source code file in standard markdown triple-backtick fences.
- **JSON** -- the model used a tool function call to return the whole source code file. This requires the LLM to wrap the code in JSON.
- **JSON (strict)** -- the same as the "JSON" strategy, but with `strict=True`. Only gpt-4o-2024-08-06 supports this setting.

The markdown strategy is the same as
aider's "whole" edit format, where the
LLM would return a source file like this:

````
Here is the program you asked for which prints "Hello":

greeting.py
```
def greeting():
    print("Hello")
```
````

The JSON and JSON (strict) strategies required the LLM to call the `write_file` function with
two parameters, as shown below.
For maximum simplicity, the LLM didn't have to specify the filename,
since the benchmark operates on one source file at a time.

```json
{
    "explanation": "Here is the program you asked for which prints \"Hello\"",
    "content": "def greeting():\n    print(\"Hello\")\n"
}
```

These strategies avoid actually *editing* source files, to keep
the task as
simple as possible.
The LLM is able to emit the whole source file intact,
which is much easier
than correctly formulating
instructions to edit
portions of a file.

This experimental setup is designed to highlight
the effects of JSON-wrapping on the LLMs ability to write code to solve a task.

## Results

Each of the 4 models was benchmarked 5 times using the different
strategies for returning code.

## Overall coding skill

As shown in Figure 1, 
all of the models did worse on the benchmark when asked to
return JSON-wrapped code in a tool function call.
Most did significantly worse, performing far below
the result obtained with the markdown strategy.

Some noteworthy observations:

- OpenAI's gpt-4o-2024-05-13 was the only model where the markdown and JSON results were
close. Using JSON only dropped the score by 0.3 percent, a difference which is
within the margin of error for 5 trials.
- The use of OpenAI's new strict mode offered no improvement
as compared to non-strict JSON.
Of course, both JSON results were well below the markdown result.
- The results from Sonnet and DeepSeek Coder suffered the worst harm from JSON wrapping.

## Syntax errors

Figure 2 shows the number of syntactic errors found in the code produced by each
model and code wrapping strategy.
Models tend to make more syntactic errors when asked to wrap code in JSON.

Sonnet avoided syntactic errors regardless of the code wrapping strategy,
but its benchmark scores in Figure 1 were lower with JSON.
This seems to indicate that JSON-wrapping 
does more than simply raise the syntactic difficulty in coding.
It may distract or challenge the model in a way that
reduces its ability to reason about coding problems.

{% include code-in-json-syntax.js %}

> Figure 2: Number of `SyntaxError` and `IndentationError` errors found in model generated code,
> totaled from 5 runs.
> Models tend to make more syntactic errors when asked to wrap code in JSON.


## Conclusions

While the quantitative results differ from the similar
[July 2023 experiments](/2023/07/02/benchmarks.html),
the conclusion seems unchanged: LLMs are bad at returning code in JSON.

OpenAI appears to be making progress in allowing LLMs to return code in
structured JSON responses without harming the code quality.
But it seems premature to consider switching from plain text
to JSON-wrapped code.


## Notes on the aider leaderboard

The results presented here are not directly comparable to results
from the main
[aider LLM leaderboard](https://aider.chat/docs/leaderboards/).
A number of settings were changed to simplify the benchmark
in order to focus on comparing plain text and JSON wrapped code.
