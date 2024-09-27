---
title: Separating code reasoning and editing
excerpt: An Architect model describes how to solve the coding problem, and an Editor model translates that into file edits. This Architect/Editor approach produces SOTA benchmark results.
highlight_image: /assets/architect.jpg
draft: true
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Separating code reasoning and editing

Aider now has experimental support for using two models to complete each coding task:

- An Architect model is asked to describe how to solve the coding problem.
- An Editor model is given the Architect's solution and asked to produce specific code editing instructions to apply those changes to source files.

Splitting up "code reasoning" and "code editing" has produced SOTA results on
[aider's code editing benchmark](/docs/benchmarks.html#the-benchmark).
It also significantly improved the benchmark scores of four of the
top coding models, as compared to their previous "solo" scores (striped bars).

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

<style>
  #passRateChart {
    max-width: 100%;
    height: auto !important;
  }
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@1.0.2"></script>
{% assign sorted_data = site.data.architect | sort: "pass_rate_2" | reverse %}
<canvas id="passRateChart" width="400" height="250"></canvas>
<script>
  document.addEventListener("DOMContentLoaded", function() {
    var ctx = document.getElementById('passRateChart').getContext('2d');
    
    // Function to determine aspect ratio and base font size based on screen width
    function getChartSettings() {
      if (window.innerWidth < 600) {
        return { aspectRatio: 1, baseFontSize: 8 }; // Slightly taller for small screens
      } else if (window.innerWidth < 800) {
        return { aspectRatio: 1.2, baseFontSize: 10 }; // Slightly taller for small screens
      } else {
        return { aspectRatio: 1.4, baseFontSize: 12 }; // Slightly taller for larger screens
      }
    }

    var chartSettings = getChartSettings();
    var baseFontSize = chartSettings.baseFontSize;

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
    var patterns = {};
    for (var key in colorMapping) {
      patterns[key] = ctx.createPattern(createStripePattern(colorMapping[key]), 'repeat');
    }
    {% assign grouped_data = sorted_data | group_by: "model" %}
    {% for group in grouped_data %}
      {% for item in group.items %}
        labels.push("{{ item.editor_model | default: "(No Editor)" }} {{ item.editor_edit_format | default: item.edit_format }}");
        data.push({{ item.pass_rate_2 }});
        if ("{{ item.editor_model }}" == "") {
          backgroundColors.push(patterns["{{ item.model }}"]);
        } else {
          backgroundColors.push(colorMapping["{{ item.model }}"]);
        }
        borderColors.push(borderColorMapping["{{ item.model }}"]);
      {% endfor %}
    {% endfor %}
    labels.reverse();
    data.reverse();
    backgroundColors.reverse();
    borderColors.reverse();
    var chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Pass Rate',
          data: data,
          backgroundColor: backgroundColors,
          borderColor: borderColors,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: chartSettings.aspectRatio,
        scales: {
          y: { 
            beginAtZero: true,
            title: {
              display: true,
              text: 'Pass Rate (%)',
              font: {
                size: baseFontSize + 6
              }
            },
            ticks: {
              font: {
                size: baseFontSize
              }
            }
          },
          x: {
            title: {
              display: true,
              text: 'Editor model and edit format',
              font: {
                size: baseFontSize + 6
              }
            },
            ticks: {
              font: {
                size: baseFontSize + 4
              },
              maxRotation: 90, // Allow full rotation if needed
              minRotation: 45  // Start rotating at 45 degrees to fit more labels
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
                  position: 'start',
                  xAdjust: 10,
                  font: {
                    size: baseFontSize
                  }
                }
              }
            }
          },
          legend: {
            display: true,
            title: {
              display: true,
              text: 'Architect model',
              font: {
                size: baseFontSize + 4,
                weight: 'bold'
              }
            },
            labels: {
              font: {
                size: baseFontSize + 4
              },
              generateLabels: function(chart) {
                var colorMapping = {
                  "o1-preview": "rgba(255, 206, 86, 0.2)",
                  "claude-3.5-sonnet": "rgba(75, 192, 192, 0.2)",
                  "gpt-4o": "rgba(54, 162, 235, 0.2)",
                  "o1-mini": "rgba(255, 99, 132, 0.2)"
                };
                return Object.keys(colorMapping).reverse().map(function(key) {
                  return {
                    text: key,
                    fillStyle: colorMapping[key],
                    strokeStyle: colorMapping[key].replace('0.2', '1'),
                    lineWidth: 1
                  };
                });
              }
            }
          }
        }
      }
    });

    // Update aspect ratio and font sizes on window resize
    window.addEventListener('resize', function() {
      var newSettings = getChartSettings();
      chart.options.aspectRatio = newSettings.aspectRatio;
      baseFontSize = newSettings.baseFontSize;
      
      // Update font sizes
      chart.options.scales.y.title.font.size = baseFontSize + 6;
      chart.options.scales.y.ticks.font.size = baseFontSize;
      chart.options.scales.x.title.font.size = baseFontSize + 6;
      chart.options.scales.x.ticks.font.size = baseFontSize + 4;
      chart.options.plugins.annotation.annotations.line1.label.font.size = baseFontSize;
      chart.options.plugins.legend.title.font.size = baseFontSize + 4;
      chart.options.plugins.legend.labels.font.size = baseFontSize + 4;
      
      chart.update();
    });
  });

  function createStripePattern(baseColor) {
    var canvas = document.createElement('canvas');
    canvas.width = 10;
    canvas.height = 10;
    var ctx = canvas.getContext('2d');

    ctx.fillStyle = baseColor;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(10, 10);
    ctx.stroke();

    return canvas;
  }
</script>

## Motivation

This approach was motivated by OpenAI's o1 models.
They are strong at reasoning, but often fail to output properly formatted
code editing instructions.
It helps to instead let them describe the solution
however they prefer and then pass that output to a more traditional LLM.
This Editor LLM can then interpret the solution description and
produce the code editing instructions needed to update
the existing source code file.

Traditional frontier models like gpt-4o and Sonnet also
seem to benefit from separating code reasoning and editing like this.
A pair of gpt-4o
or a pair of Sonnet models
in Architect/Editor configuration outperform their previous solo benchmark results.

Another reason why this approach is newly viable is that the
speed and costs of frontier models have been rapidly improving.
In particular, chaining older LLMs would have been quite slow and
contrary to aider's goal of providing a rapid, interactive,
pair programming AI coding experience.

## Code reasoning and code editing

Aider uses a variety of 
[edit formats](/docs/more/edit-formats.html)
to allow LLMs to specify edits to local source files.
All of aider's editing formats require the LLM to return source code edits in a specific text
format, so that aider can process the edits and apply them to the local source files.

Normally aider asks the model to solve a coding problem in one prompt,
asking the LLM to explain the solution and return 
a well formatted series of file edits.
Because this all happens in a single prompt/response round trip to the LLM,
the model has to split its attention between 
solving the coding problem and conforming to the edit format.

The Architect/Editor approach splits this into two inference steps, possibly
using two different LLMs:

1. Ask how to solve the coding problem (Architect).
2. Turn the proposed solution into a series of well formed code edits (Editor).

The Architect/Editor approach allows the Architect to focus on solving the coding problem
and describe the solution however comes naturally to it.
This gives the Architect more reasoning capacity to focus just on solving the coding
task.
We can also assign the Architect task to a strong reasoning model like o1-preview,
and give the editing task to an appropriate model based on cost, editing skill, etc.
Similarly, the Editor can focus all of its attention on properly formatting the edits
without needing to reason much about how to solve the coding problem.

## Results

The graph above and the table below show the
[aider's code editing benchmark](/docs/benchmarks.html#the-benchmark)
score for various combinations of Architect and Editor models.


Some noteworthy observations:

- Pairing o1-preview as Architect with Deepseek as Editor sets a SOTA significantly above the previous best score. This result is obtained with Deepseek using the "whole" editing format, requiring it to output a full update copy of each edited source file. Both of these steps are therefore quite slow, so probably not practical for interactive use with aider.
- Pairing OpenAI's o1-preview with Anthropic's Sonnet as the Editor produces the second best result. This is an entirely practical configuration for users able to work with both providers.
- Pairing Sonnet/Sonnet and GPT-4o/GPT-4o provides significant lift for both models compared to their solo results, especially for GPT-4o.
- Deepseek is surprisingly effective as an Editor model. It seems remarkably capable at turning proposed coding solutions into new, updated versions of the source files. Using the efficient "diff" editing format, Deepseek helps all the Architect models except for Sonnet.

## Try it!

The development version of aider 
has built in defaults to support Architect/Editor coding with
OpenAI's o1 models, gpt-4o and Anthropic's Claude 3.5 Sonnet.
Run aider with `--architect` or get started quickly like this:

```
pip install -U git+https://github.com/paul-gauthier/aider.git

# Change directory into a git repo
cd /to/your/git/repo

# Work with Claude 3.5 Sonnet as the Architect and Editor
export ANTHROPIC_API_KEY=your-key-goes-here
aider --sonnet --architect

# Work with OpenAI models, using gpt-4o as the Editor
export OPENAI_API_KEY=your-key-goes-here
aider --4o --architect
aider --o1-mini --architect
aider --o1-preview --architect
```

## Full results


<table>
  <thead>
    <tr>
      <th>Architect</th>
      <th>Editor</th>
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
          <td>{{ item.editor_model }}</td>
          <td style="text-align: center;">{{ item.editor_edit_format | default: item.edit_format }}</td>
          <td style="text-align: right;">{{ item.pass_rate_2 }}%</td>
          <!-- <td style="text-align: right;">${{ item.total_cost | round: 2 }}</td> -->
        </tr>
      {% endfor %}
    {% endfor %}
  </tbody>
</table>


