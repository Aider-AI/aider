---
title: LLMs are bad at returning code in json
excerpt: LLMs write worse code if you ask them to return the code wrapped in json (via a tool or function call).
highlight_image: /assets/code-in-json.jpg
draft: true
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# LLMs are bad at returning code in json


<canvas id="passRateChart" width="800" height="400" style="margin-bottom: 20px"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('passRateChart').getContext('2d');
    
    var yamlData = {{ site.data.code-in-json | jsonify }};
    
    var models = [...new Set(yamlData.map(item => item.model))];
    var editFormats = [...new Set(yamlData.map(item => item.edit_format))];
    
    var datasets = editFormats.map(format => ({
        label: format,
        data: models.map(model => {
            var item = yamlData.find(d => d.model === model && d.edit_format === format);
            return item ? item.pass_rate_1 : null;
        }),
        backgroundColor: function(context) {
            const format = context.dataset.label;
            if (format === 'Markdown') {
                return 'rgba(54, 162, 235, 0.8)';
            } else if (format.startsWith('Tool call')) {
                const ctx = context.chart.ctx;
                const gradient = ctx.createPattern(createStripedCanvas(format === 'Tool call (strict)'), 'repeat');
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
                        text: 'Pass Rate (%)'
                    },
                    max: 70
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Pass rate by model and code return strategy',
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

The newest LLMs have support for returning properly formatted json responses,
making it easy for client applications to parse complex responses.
This makes it tempting for AI coding applications to
use tool function calls or other structured reply formats to
receive code from LLMs.
Unfortunately, 
LLMs write worse code when asked to wrap it in json, harming their ability
to correctly solve coding tasks.
Returning code as plain (markdown) text results in an average of 6% higher scores
on a variant of the aider code editing benchmark.
This holds true across many top coding LLMs, 
and even OpenAI's newest gpt-4o-2024-08-06 with "strict" json support
suffers from this code-in-json handicap.

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
and parse a nicely formatted json 
response:

```
{
    "filename": "greeting.py",
    "search": "def greeting():\n    print(\"Hello\")\n"
    "replace": "def greeting():\n    print(\"Goodbye\")\n"
}
```

This has become even more tempting as LLM providers
continue to improve their tooling for reliably generating
valid json.
For example, OpenAI recently announced the ability to
[strictly enforce that json responses will be syntactically correct 
and conform to a specified schema](https://openai.com/index/introducing-structured-outputs-in-the-api/).

But producing valid (schema compliant) json is not sufficient for this use case.
The json also has to contain valid, high quality code.
And unfortunately, 
LLMs write worse code when they're asked to 
wrap it in json.

In some sense this shouldn't be surprising.
Just look at the very simple
json example above, with the escaped 
quotes `\"` and
newlines `\n`
mixed into the code.
Imagine if the code itself contained json or other quoted strings,
with their
own escape sequences.

If you tried to write a program, 
would you do a better job
typing it out normally
or as a properly escaped 
json string?


## Quantifying the benefits of plain text

Previous [aider benchmark results](/2023/07/02/benchmarks.html)
showed
the superiority of returning code
as plain text coding compared to json-wrapped function calls.
Those results were obtained
over a year ago, against far less
capable models.
OpenAI's newly announced support for "strict" json seemed like a good reason to
investigate whether the newest models are still handicapped by json-wrapping code.

The graph above shows benchmark
results from 
3 of the strongest code editing models:

- gpt-4o-2024-08-06
- claude-3-5-sonnet-20240620
- deepseek-coder (V2 0724)

Each model was given one try to solve 
[133 practice exercises from the Exercism python repository](/2023/07/02/benchmarks.html#the-benchmark).
This is the standard aider "code editing" benchmark, but restricted to a single attempt
without a second try to "fix" any errors.

Each model was assessed by the benchmark using two 
different strategies for returning code:

- **Markdown** -- the model returned the whole source code file in standard markdown triple-backtick fences.
- **Tool call** -- the model used a tool function call to return the whole source code file. This requires the LLM to wrap the code in json.

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

The tool strategy requires the LLM to call the `write_file` function with
two parameters, as shown below.
For maximum simplicity, the LLM didn't even have to specify the filename,
since the benchmark operates only on a single source file.

```
{
    "explanation": "Here is the program you asked for which prints \"Hello\"",
    "content": "def greeting():\n    print(\"Hello\")\n"
}
```

Both of these formats avoid actually *editing* source files, to keep
the task as
simple as possible.
The LLM is able to emit the whole source file intact,
which is much easier
than correctly formulating
instructions to edit
portions of a file.

This experimental setup is designed to highlight
the effects of json-wrapping on the LLMs ability to write code to solve a task.

## Results

All 3 models did significantly worse on the benchmark when asked to
return json-wrapped code in a tool function call.
