---
title: A draft post.
excerpt: With a draft summary.
highlight_image: /assets/linting.jpg
draft: true
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Separating code reasoning and editing

Aider now has experimental support for using two models to complete each coding task:

- A Senior model is asked to describe how to solve the coding problem in detail.
- A Junior model is given the Senior's solution and asked to produce specific code editing instructions to apply those changes to source files.

Splitting up "code reasoning" and "code editing" has produced SOTA results on
[aider's code editing benchmark](/docs/benchmarks.html#the-benchmark).
Both Sonnet and o1-preview exceed the preivous SOTA when using this
new Senior/Junior approach.
The best result was obtained with
o1-preview as Senior and Deepseek as Junior, raising the SOTA from 79.7% up to 85%!

<style>
  .shaded td {
    background-color: #f2f2f2;
    border-top: 1px solid #ccc;
  }
  table {
    border-collapse: collapse;
    width: 100%;
  }
  th {
    padding: 8px;
    text-align: left;
    border-bottom: 1px solid #ddd;
  }
  th {
    background-color: #e2e2e2;
  }
</style>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@1.0.2"></script>
{% assign sorted_data = site.data.senior | sort: "pass_rate_2" | reverse %}
<canvas id="passRateChart" width="400" height="300"></canvas>
<script>
  document.addEventListener("DOMContentLoaded", function() {
    var ctx = document.getElementById('passRateChart').getContext('2d');
    var labels = [];
    var data = [];
    var colorMapping = {
      "claude-3.5-sonnet": "rgba(75, 192, 192, 0.2)",
      "o1-mini": "rgba(255, 99, 132, 0.2)",
      "gpt-4o": "rgba(54, 162, 235, 0.2)",
      "o1-preview": "rgba(255, 206, 86, 0.2)"
    };
    var borderColorMapping = {
      "claude-3.5-sonnet": "rgba(75, 192, 192, 1)",
      "o1-mini": "rgba(255, 99, 132, 1)",
      "gpt-4o": "rgba(54, 162, 235, 1)",
      "o1-preview": "rgba(255, 206, 86, 1)"
    };
    var backgroundColors = [];
    var borderColors = [];
    {% assign grouped_data = sorted_data | group_by: "model" %}
    {% for group in grouped_data %}
      {% for item in group.items %}
        labels.push("{{ item.junior_model | default: "(No Junior)" }} {{ item.junior_edit_format | default: item.edit_format }}");
        data.push({{ item.pass_rate_2 }});
        var bgColor = colorMapping["{{ item.model }}"];
        if ("{{ item.junior_model }}" === "deepseek") {
          if ("{{ item.junior_edit_format }}" === "whole") {
            bgColor = createStripedPattern(bgColor);
          } else if ("{{ item.junior_edit_format }}" === "diff") {
            bgColor = createPolkaDotPattern(bgColor);
          }
        }
        backgroundColors.push(bgColor);
        borderColors.push(borderColorMapping["{{ item.model }}"]);
      {% endfor %}
    {% endfor %}

    function createStripedPattern(color) {
      var canvas = document.createElement('canvas');
      var ctx = canvas.getContext('2d');
      canvas.width = 10;
      canvas.height = 10;
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 10, 10);
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(10, 10);
      ctx.stroke();
      return ctx.createPattern(canvas, 'repeat');
    }

    function createPolkaDotPattern(color) {
      var canvas = document.createElement('canvas');
      var ctx = canvas.getContext('2d');
      canvas.width = 10;
      canvas.height = 10;
      ctx.fillStyle = color;
      ctx.fillRect(0, 0, 10, 10);
      ctx.fillStyle = 'white';
      ctx.beginPath();
      ctx.arc(5, 5, 2, 0, Math.PI * 2);
      ctx.fill();
      return ctx.createPattern(canvas, 'repeat');
    }
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Pass Rate',
          data: data,
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1,
          backgroundColor: backgroundColors,
          borderColor: borderColors
        }]
      },
      options: {
        scales: {
          y: { 
            beginAtZero: true,
            title: {
              display: true,
              text: 'Pass Rate (%)'
            }
          },
          x: {
            title: {
              display: true,
              text: 'Junior model and edit format'
            }
          }
        },
        plugins: {
          annotation: {
            annotations: {
              line1: {
                type: 'line',
                yMin: 79.7,
                yMax: 79.7,
                borderColor: 'rgba(255, 99, 132, 0.8)',
                borderWidth: 2,
                borderDash: [6, 6],
                label: {
                  content: 'Previous SOTA',
                  enabled: true,
                  position: 'end'
                }
              }
            }
          },
          legend: {
            display: true,
            labels: {
              generateLabels: function(chart) {
                var colorMapping = {
                  "o1-preview": "rgba(255, 206, 86, 0.2)",
                  "claude-3.5-sonnet": "rgba(75, 192, 192, 0.2)",
                  "gpt-4o": "rgba(54, 162, 235, 0.2)",
                  "o1-mini": "rgba(255, 99, 132, 0.2)"
                };
                return Object.keys(colorMapping).map(function(key) {
                  var fillStyle = colorMapping[key];
                  if (chart.data.labels.some(label => label.includes('deepseek whole'))) {
                    fillStyle = createStripedPattern(fillStyle);
                  } else if (chart.data.labels.some(label => label.includes('deepseek diff'))) {
                    fillStyle = createPolkaDotPattern(fillStyle);
                  }
                  return {
                    text: key,
                    fillStyle: fillStyle,
                    strokeStyle: colorMapping[key].replace('0.2', '1'),
                    lineWidth: 1
                  };
                });
              }
            }
          }
      }
    }});
  });
</script>

## Motivation

This approach was motivated by OpenAI's o1 models.
They are strong at reasoning, but often fail to output well formed
code editing instructions.
It helps to instead let them describe the solution
however they prefer and then pass that output to a more traditional LLM.
The traditional LLM can then
produce the specific code edits needed to update
the existing source code file.

Traditional frontier models like gpt-4o and Sonnet also
seem to benefit from separating code reasoning and editing.
A pair of gpt-4o
or a pair of Sonnet models
in Senior/Junior configuration outperform their previous benchmark results.

Another reason why this approach is newly viable is that the
speed and costs of frontier models have been rapidly improving.
In particular, chaining older LLMs would have been quite slow and
contrary to aider's goal of providing a rapid, interactive,
pair programming AI coding experience.

## Results

The graph above and the table below show the
[aider's code editing benchmark](/docs/benchmarks.html#the-benchmark)
score for various combinations of Senior and Junior models.


Some noteworthy observations:

- Pairing o1-preview as Senior with Deepseek as Junior sets a SOTA significantly above the previous best. This result is obtained with Deepseek using the "whole" editing format, requiring it to output a full update copy of each edited source file. This is quite slow, and so probably not practical for interactive use with aider.
- Pairing OpenAI's o1-preview with Anthropic's Sonnet as the Junior produces the second best result, and is an entirely practical configuration for users able to work with both providers.
- Pairing Sonnet/Sonnet and GPT-4o/GPT-4o provides significant lift for both models, especially for GPT-4o.
- Deepseek is surprisingly effective as a Junior model. It seems remarkably capable at turning proposed coding solutions into new, updated versions of the source files. Using the efficient "diff" editing format, Deepseek helps all the Senior models except for Sonnet.

## Related work

This approach is somewhat similar to 
[Cursor's "Instant Apply"](https://fireworks.ai/blog/cursor) feature.
The main differences are:

- Aider can flexibly use any off the shelf model as the Junior.
- Aider' Junior model can use the efficient "diff" editing format to specify source code changes as a series of search/replace operations. Cursor's instant apply models essentially use the "whole" edit format, asking the model to output a full, updated copy of each edited source file.
- Cursor's apply model is highly optimized for speed and reaches 1,000 tokens/second, which mitigates the delays associated with outputting whole copies of edited files.

## Try it

Aider has built in defaults to support Senior/Junior coding with
OpenAI's o1 models, gpt-4o and Anthropic's Claude 3.5 Sonnet.
Run aider with `--senior` or get started quickly like this:

```
pip install -U aider-chat

# Change directory into a git repo
cd /to/your/git/repo

# Work with Claude 3.5 Sonnet as the Senior and Junior
export ANTHROPIC_API_KEY=your-key-goes-here
aider --sonnet --senior

# Work with OpenAI models, using gpt-4o as the Junior
export OPENAI_API_KEY=your-key-goes-here
aider --4o --senior
aider --o1-mini --senior
aider --o1-preview --senior
```

## Full results


<table>
  <thead>
    <tr>
      <th>Senior</th>
      <th>Junior</th>
      <th>Edit Format</th>
      <th>Pass Rate</th>
    </tr>
  </thead>
  <tbody>
    {% for group in grouped_data %}
      {% assign group_class = forloop.index | modulo: 2 | plus: 1 %}
      {% for item in group.items %}
        <tr class="{% if group_class == 1 %}shaded{% endif %}">
          <td>{{ item.model }}</td>
          <td>{{ item.junior_model }}</td>
          <td style="text-align: center;">{{ item.junior_edit_format | default: item.edit_format }}</td>
          <td style="text-align: right;">{{ item.pass_rate_2 }}%</td>
          <!-- <td style="text-align: right;">${{ item.total_cost | round: 2 }}</td> -->
        </tr>
      {% endfor %}
    {% endfor %}
  </tbody>
</table>


