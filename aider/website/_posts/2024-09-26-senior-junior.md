---
title: Separating code reasoning and editing
excerpt: A Senior model describes how to solve the coding problem, and a Junior model translates that into file edits. This Senior/Junior approach produces SOTA benchmark results.
highlight_image: /assets/senior.jpg
draft: true
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Separating code reasoning and editing

Aider now has experimental support for using two models to complete each coding task:

- A Senior model is asked to describe how to solve the coding problem.
- A Junior model is given the Senior's solution and asked to produce specific code editing instructions to apply those changes to source files.

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

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@1.0.2"></script>
{% assign sorted_data = site.data.senior | sort: "pass_rate_2" | reverse %}
<canvas id="passRateChart" width="400" height="250"></canvas>
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
    var patterns = {};
    for (var key in colorMapping) {
      patterns[key] = ctx.createPattern(createStripePattern(colorMapping[key]), 'repeat');
    }
    {% assign grouped_data = sorted_data | group_by: "model" %}
    {% for group in grouped_data %}
      {% for item in group.items %}
        labels.push("{{ item.junior_model | default: "(No Junior)" }} {{ item.junior_edit_format | default: item.edit_format }}");
        data.push({{ item.pass_rate_2 }});
        if ("{{ item.junior_model }}" == "") {
          backgroundColors.push(patterns["{{ item.model }}"]);
        } else {
          backgroundColors.push(colorMapping["{{ item.model }}"]);
        }
        borderColors.push(borderColorMapping["{{ item.model }}"]);
      {% endfor %}
    {% endfor %}
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
              text: 'Pass Rate (%)',
              font: {
                size: 18
              }
            },
            ticks: {
              font: {
                size: 12
              }
            }
          },
          x: {
            title: {
              display: true,
              text: 'Junior model and edit format',
              font: {
                size: 18
              }
            },
            ticks: {
              font: {
                size: 16
              }
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
                  position: 'end',
                  font: {
                    size: 14
                  }
                }
              }
            }
          },
          legend: {
            display: true,
            labels: {
              font: {
                size: 16
              },
              generateLabels: function(chart) {
                var colorMapping = {
                  "o1-preview": "rgba(255, 206, 86, 0.2)",
                  "claude-3.5-sonnet": "rgba(75, 192, 192, 0.2)",
                  "gpt-4o": "rgba(54, 162, 235, 0.2)",
                  "o1-mini": "rgba(255, 99, 132, 0.2)"
                };
                return Object.keys(colorMapping).map(function(key) {
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
    }});
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

### **Motivation**

The latest advancements in Aider are inspired by the strengths and limitations of various language models, particularly OpenAI's O1 series. These models exhibit exceptional reasoning capabilities but often struggle with producing properly formatted code editing instructions. To leverage their strengths, Aider introduces a new approach that separates the tasks of problem-solving and code editing into distinct roles, handled by different models.

By allowing models like O1-preview to focus solely on reasoning and planning (the "Architect"), and passing their solutions to another model specialized in code editing (the "Editor"), Aider enhances the efficiency and effectiveness of the code generation process. This separation aligns with the natural capabilities of different models and leads to better overall performance.

Moreover, the speed and cost improvements in frontier models make this multi-model approach practical for interactive use. Chaining models no longer compromises the responsiveness that is crucial for an effective pair programming experience.

### **Introducing Different Modes in Aider**

To accommodate various coding tasks and user preferences, Aider now offers multiple operational modes:

1. **Standard Mode (`/code`)**: This is the traditional Aider experience, ideal for quick edits and straightforward coding tasks. It uses a single model to handle both reasoning and code generation in one step.

2. **Architect Mode (`/architect`)**: This mode activates the two-step Architect/Editor process, suitable for complex tasks that require deep reasoning and careful planning. The Architect model generates a detailed solution, and the Editor model applies the changes to your codebase.

3. **Ask Mode (`/ask`)**: Allows you to discuss or understand your code without making changes. It's useful for getting explanations or exploring ideas.

### **Models and Their Roles**

Aider allows you to specify different models for each role to optimize performance and cost:

- **Architect Model**: Focused on reasoning and planning. Ideal models include OpenAI's O1-preview, which excels at problem-solving but may not format code edits precisely.

- **Standard Model**: Handles regular coding tasks in Standard Mode. Models like Claude 3.5 Sonnet are balanced for both reasoning and code generation.

- **Editor Model**: Specialized in applying code changes accurately. Models like Deepseek 2.5 are efficient at translating solutions into code edits.

### **How It Works**

#### **Standard Mode (`/code` or default)**

- **Usage**: Ideal for quick, simple edits.
- **Process**: You provide a prompt, and the Standard Model generates and applies the code changes in one step.
- **Example**:

  ```plaintext
  User: Add a new function to calculate the factorial of a number.
  Aider (Standard Model): [Generates and applies the code for the factorial function.]
  ```

#### **Architect Mode (`/architect`)**

- **Usage**: Best for complex tasks that require detailed planning.
- **Process**:

  1. **Architect Phase**:
     - **Model**: Architect Model (e.g., O1-preview).
     - **Task**: Generates a detailed plan or solution description.
  2. **Confirmation**:
     - Aider presents the plan and asks for your approval.
  3. **Editor Phase**:
     - **Model**: Editor Model (e.g., Deepseek 2.5).
     - **Task**: Applies the code changes based on the Architect's plan.

- **Example**:

  ```plaintext
  User: /architect Implement JWT authentication in the application.

  Architect Model: [Provides a detailed plan on how to implement JWT authentication.]

  Aider: The Architect has proposed a plan. Do you want the Editor to apply these changes? (yes/no)

  User: yes

  Editor Model: [Applies the code changes as per the plan.]
  ```

#### **Ask Mode (`/ask`)**

- **Usage**: When you need explanations or want to discuss code without making changes.
- **Process**: The model provides insights or answers to your questions.

- **Example**:

  ```plaintext
  User: /ask Can you explain how the authentication middleware works?

  Aider: [Provides an explanation of the authentication middleware.]
  ```

### **Switching Between Modes**

Aider provides flexibility in switching between modes:

- **Commands**:

  - `/mode standard` or `/code`: Switch to Standard Mode.
  - `/mode architect` or `/architect`: Activate Architect Mode.
  - `/ask`: Enter Ask Mode for discussions.

- **Prompt Prefixes**:

  - Start your prompt with `architect:` to use Architect Mode for that request.
  - Start with `code:` or `edit:` to ensure the prompt is handled in Standard Mode.

- **Dynamic Switching**: You can switch modes at any time without restarting Aider, allowing you to adapt to the task at hand seamlessly.

### **Configuring Models**

You can specify which models to use for each role, tailoring Aider to your needs:

- **Command-Line Arguments**:

  ```bash
  aider --architect-model o1-preview --standard-model sonnet-3.5 --editor-model deepseek-2.5
  ```

- **In-Session Commands**:

  - `/use_architect_model [model_name]`: Change the Architect Model.
  - `/use_standard_model [model_name]`: Change the Standard Model.
  - `/use_editor_model [model_name]`: Change the Editor Model.

- **Configuration File (`.aiderrc`)**:

  ```yaml
  default_mode: standard
  architect_model: o1-preview
  standard_model: sonnet-3.5
  editor_model: deepseek-2.5
  ```

### **Optimizing Your Workflow**

- **Default to Fast Mode**: For most tasks, especially simple edits, use Standard Mode for speed and efficiency.

- **Invoke Architect Mode When Needed**: For complex features, debugging, or when you're stuck, switch to Architect Mode to benefit from detailed planning and problem-solving.

- **Leverage the Implementor (Editor) Model**: Use models like Deepseek 2.5 as the Editor for fast and accurate application of code changes.

### **Results**

The adoption of this multi-model, multi-mode approach has led to significant performance improvements in Aider's [code editing benchmark](/docs/benchmarks.html#the-benchmark).

**Key Observations**:

- **Architect/Editor Pairings**: Combining a strong reasoning model with an efficient editor enhances performance, especially for complex tasks.

- **Flexible Model Selection**: Users can balance cost and speed by choosing models appropriate for each role.

- **Improved User Experience**: The ability to switch modes and models without restarting Aider streamlines the development process.

### **Try It Out!**

Experience the new modes and model configurations by updating Aider and experimenting with different setups.

**Installation**:

```bash
pip install -U git+https://github.com/paul-gauthier/aider.git
```

**Setup**:

- **Navigate to your git repository**:

  ```bash
  cd /path/to/your/git/repo
  ```

- **Set API Keys**:

  ```bash
  export OPENAI_API_KEY=your-openai-key
  export ANTHROPIC_API_KEY=your-anthropic-key
  ```

**Examples**:

- **Using Standard Mode with Claude 3.5 Sonnet**:

  ```bash
  aider --sonnet
  ```

- **Using Architect Mode with O1-preview and Deepseek 2.5**:

  ```bash
  aider --architect-model o1-preview --editor-model deepseek-2.5
  ```

- **Switching Modes In-Session**:

  ```plaintext
  User: /mode architect
  User: Implement a caching mechanism to improve performance.
  ```

- **Specifying Models In-Session**:

  ```plaintext
  User: /use_architect_model o1-mini
  User: /use_editor_model sonnet-3.5
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


