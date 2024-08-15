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


<canvas id="passRateChart" width="800" height="400" style="margin-bottom: 20px"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('passRateChart').getContext('2d');
    
    var yamlData = {{ site.data.code-in-json | jsonify }};
    
    var models = [...new Set(yamlData.map(item => item.model))].sort();
    var editFormats = [...new Set(yamlData.map(item => item.edit_format))];
    
    var datasets = editFormats.map(format => ({
        label: format,
        data: models.map(model => {
            var items = yamlData.filter(d => d.model === model && d.edit_format === format);
            if (items.length === 0) return null;
            var average = items.reduce((sum, item) => sum + item.pass_rate_1, 0) / items.length;
            return parseFloat(average.toFixed(1));
        }),
        backgroundColor: function(context) {
            const format = context.dataset.label;
            if (format === 'Markdown') {
                return 'rgba(54, 162, 235, 0.8)';
            } else if (format.startsWith('JSON')) {
                const ctx = context.chart.ctx;
                const gradient = ctx.createPattern(createStripedCanvas(format === 'JSON (strict)'), 'repeat');
                return gradient;
            } else {
                return 'rgba(75, 192, 192, 0.8)';
            }
        },
    }));

    var data = {
        labels: models,
        datasets: datasets
    };

    var config = {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Model'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Pass Rate (%, average of 5 runs)'
                    },
                    max: 70
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Pass rate by model and code wrapping strategy',
                    font: {
                        size: 16
                    }
                },
                legend: {
                    position: 'top',
                }
            }
        }
    };

    function createStripedCanvas(isStrict) {
        const patternCanvas = document.createElement('canvas');
        const patternContext = patternCanvas.getContext('2d');
        const size = 10;
        patternCanvas.width = size;
        patternCanvas.height = size;

        patternContext.fillStyle = 'rgba(255, 99, 132, 0.8)';
        patternContext.fillRect(0, 0, size, size);

        if (isStrict) {
            patternContext.strokeStyle = 'rgba(255, 255, 255, 0.8)';
            patternContext.lineWidth = 0.75;
            patternContext.beginPath();
            patternContext.moveTo(0, 0);
            patternContext.lineTo(size, size);
            patternContext.stroke();
        }

        return patternCanvas;
    }

    new Chart(ctx, config);
});
</script>


## Abstract

The newest LLMs have support for returning properly formatted JSON responses,
making it easy for client applications to parse complex responses.
This makes it tempting for AI coding applications to
use tool function calls or other structured reply formats to
receive code from LLMs.
Unfortunately, 
LLMs write worse code when asked to wrap it in JSON, harming their ability
to correctly solve coding tasks.
On a variant of the aider code editing benchmark, 
JSON-wrapping code
often significantly harms coding
performance
compared to returning code as plain (markdown) text.
This holds true across many top coding LLMs, 
and even OpenAI's newest gpt-4o-2024-08-06 with "strict" JSON support
suffers from this code-in-JSON handicap.

## Introduction

A lot of people wonder why aider doesn't tell LLMs to
use tools or function calls to
specify code edits.
Instead, aider asks for code edits in plain text, like this:

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

People expect that it would be easier and more reliable to use tool calls,
which would return a structured JSON response:

```
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

But producing valid (schema compliant) JSON is not sufficient for this use case.
The JSON also has to contain valid, high quality code.
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
if the code itself contained JSON or other quoted strings,
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

The graph above shows benchmark
results from 
4 of the strongest code editing models:

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

```
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
The results in the graph are the average of 5 runs for each
model & strategy combination.

## Results


## Overall coding skill

All of the models did worse on the benchmark when asked to
return JSON-wrapped code in a tool function call.
Most did significantly worse, performing far below
the result obtained with the markdown strategy.

Some noteworthy observations:

- OpenAI's gpt-4o-2024-05-13 was the only model where the markdown and JSON results were
close. Using JSON only dropped the score by 0.3 percent, a difference which is
probably within the margin of error for 5 trials.
- The use of OpenAI's new strict mode seemed to harm the results for gpt-4o-2024-08-06
as compared to non-strict JSON. 
Of course, both JSON results were well below the markdown result.
- The results from Sonnet and DeepSeek Coder suffered the worst harm from JSON wrapping.

## Syntax errors


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
