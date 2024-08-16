---
title: LLMs are bad at returning code in JSON
excerpt: LLMs write worse code if you ask them to return the code wrapped in JSON via a tool function call.
highlight_image: /assets/code-in-json.jpg
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# LLMs are bad at returning code in JSON


LLMs produce lower quality code if they’re asked to return it as part of a structured JSON response. This seems to be true for many top models, including those with specialized support for JSON. Benchmarks show that models struggle with syntax errors in the code
they write, related to quoting and escaping it into JSON.
The benchmark results also imply a decreased capacity for solving coding problems due to the burden of JSON formatting. 

{% include code-in-json-benchmark.js %}

> Figure 1: Aider coding benchmark scores of models using either plain markdown text or JSON to return code.
> Pass rate (%) averaged over 5 runs.
> Models produce better code when they return it as markdown text,
> as compared to returning code in a structured JSON response.


## Background

People often ask why aider uses a plain text format for LLMs to specify code edits (below),
rather than relying on LLM tools and structured JSON responses.

```python
greeting.py
<<<<<<< SEARCH
def greeting():
    print("Hello")
=======
def greeting():
    print("Goodbye")
>>>>>>> REPLACE
```

People expect that it would be easier and more reliable to use tool calls,
which would involve a structured JSON response more like this:

```json
{
    "filename": "greeting.py",
    "search": "def greeting():\n    print(\"Hello\")\n"
    "replace": "def greeting():\n    print(\"Goodbye\")\n"
}
```

This question becomes increasingly relevant as LLM providers
continue to improve their tooling for reliably generating JSON.
For example, 
[OpenAI recently announced](https://openai.com/index/introducing-structured-outputs-in-the-api/)
the ability to
strictly enforce that JSON responses will be syntactically correct 
and conform to a specified schema.

But just producing valid JSON is not sufficient for AI code generation --
the code inside the JSON matters too.
It has to be high quality code that solves the assigned coding task without errors or bugs.
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
or typing it as a properly escaped 
JSON string?


## Quantifying the benefits of plain text

Previous [aider benchmark results](/2023/07/02/benchmarks.html)
showed
the superiority of returning code
as plain text compared to JSON-wrapped function calls.
Those results were obtained
over a year ago, against models far less capable than those available today.
OpenAI's newly announced support for "strict" JSON
suggests the possibility that modern models might be able
to return quality code inside a structured JSON response.

The results presented here are based on
the 
[aider "code editing" benchmark](/2023/07/02/benchmarks.html#the-benchmark)
of 133 practice exercises from the Exercism python repository.
The benchmark was simplified somewhat to focus on the differences between
plain text and JSON responses.
In particular, models were 
restricted to a single attempt to solve each task
without a second try to fix errors.

The performance of each model was compared across different strategies for returning code:

- **Markdown** -- the model returned the whole source code file in standard markdown triple-backtick fences.
- **JSON** -- the model used a tool function call to return the whole source code file in a structured JSON response.
- **JSON (strict)** -- the same as the "JSON" strategy, but with `strict=True`. Only gpt-4o-2024-08-06 supported this setting.

The markdown strategy was the same as
aider's "whole" edit format, where the
LLM returns an entire updated copy of the source file like this:

````
Here is the program you asked for which prints "Hello":

greeting.py
```
def greeting():
    print("Hello")
```
````

Both JSON strategies required the LLM to call the `write_file` function with
an explanation/plan and
the entire updated copy of the source file.
The LLM didn't have to specify the filename,
since the benchmark operates on one source file at a time.

```json
{
    "explanation": "Here is the program you asked for which prints \"Hello\"",
    "content": "def greeting():\n    print(\"Hello\")\n"
}
```

This experimental setup was designed to quantify
the effects of JSON-wrapping on the LLMs ability to write code to solve a task.

## Results

Four of the strongest code editing models were benchmarked
to assess the impact of JSON-wrapping code:

- claude-3-5-sonnet-20240620
- deepseek-coder (V2 0724)
- gpt-4o-2024-05-13
- gpt-4o-2024-08-06

Each combination of model and code wrapping strategy was benchmarked 5 times
on all 133 problems.

### Overall coding skill

As shown in Figure 1, 
all of the models did worse on the benchmark when asked to
return code in a structured JSON response.
Most did significantly worse, performing well below
their result with the markdown strategy.

Some noteworthy observations:

- OpenAI's gpt-4o-2024-05-13 was the only model where the markdown and JSON results were
close. Using JSON only dropped the score by 0.4 percent, a difference which is
within the margin of error for 5 trials.
- The use of OpenAI's new strict mode offered no improvement
as compared to non-strict JSON.
Both JSON results were well below the markdown result.
- The results from Sonnet and DeepSeek Coder suffered the worst harm from JSON wrapping.

### Syntax errors

Models tend to make more syntax errors *in the code they write*
when asked to wrap it in JSON.
The models can reliably 
produce valid JSON, but code inside is more prone to syntax errors.

Figure 2 shows the number of syntax errors found in the code produced by each
model and code wrapping strategy.
It totals up the `SyntaxError` and `IndentationError` errors from all 5 runs,
for each model and strategy combination.

Below is an example of a `SyntaxError` created by gpt-4o-2024-05-13 using the
JSON code wrapping strategy.
It appears that the model got confused about escaping and quoting while trying
to format the JSON response.

```python
Traceback (most recent call last):
  ...   
  File "bottle-song/bottle_song.py", line 9
    lyrics.append(f'There'll be {i - 1} green bottles hanging on the wall.')
                                                                          ^
SyntaxError: unterminated string literal (detected at line 9)
```

The problematic line of code contains a single-quoted string which also
contains a single-quote character.
It should have been output as the following chunk of JSON, with
a double slash in `There\\'ll`.
That is needed to JSON-escape the `\` so that it survives
JSON-decoding to 
produce `There\'ll` in the resulting code.
That would correctly escape the single-quote inside the single-quoted string.

```
...lyrics.append(f'There\\'ll be {i - 1} green bottles hanging on the wall.')\n...
```



{% include code-in-json-syntax.js %}

> Figure 2: Number of `SyntaxError` and `IndentationError` errors found in model generated code,
> totaled from 5 runs.
> Models tend to make more syntax and formatting errors when asked to wrap code in JSON.

### Beyond syntax errors

Sonnet's results seems to indicate that the negative effects of JSON-wrapping 
go beyond just syntactic difficulties.
Sonnet avoided syntax errors regardless of the code wrapping strategy,
but its benchmark scores in Figure 1 were nonetheless lower with JSON.
This implies that JSON-wrapping may distract or challenge models in a way that
reduces their ability to reason about solving coding problems.



## Conclusions

While the specific results differ from the similar
[July 2023 experiments](/2023/07/02/benchmarks.html),
the conclusion remains unchanged: LLMs are bad at returning code in
structured JSON responses.

OpenAI appears to be making progress in allowing LLMs to
return JSON-wrapped code
without harming the code quality.
But it seems premature to consider switching from plain text
to JSON-wrapped code at this time.

---------

#### Notes on the aider leaderboard

*The results presented here are not directly comparable to results
from the main
[aider LLM leaderboard](https://aider.chat/docs/leaderboards/).
A number of settings were changed to simplify the benchmark
in order to focus on comparing plain text and JSON-wrapped code.*
