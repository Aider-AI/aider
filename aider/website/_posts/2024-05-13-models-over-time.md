---
title: Drawing graphs with aider, GPT-4o and matplotlib
excerpt: Use GPT-4o to draw graphs with matplotlib, including adjusting styles and making visual changes. You get the graph, but you also get the code in your repo.
highlight_image: /assets/models-over-time.png
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

![LLM coding skill over time](/assets/models-over-time.svg)

# Drawing graphs with aider, GPT-4o and matplotlib

I recently wanted to draw a graph showing how LLM code editing skill has been
changing over time as new models have been released by OpenAI, Anthropic and others.
I have all the
[data in a yaml file](https://github.com/Aider-AI/aider/blob/main/website/_data/edit_leaderboard.yml) that is used to render
[aider's LLM leaderboards](https://aider.chat/docs/leaderboards/).

Below is the aider chat transcript, which shows:

- I launch aider with the yaml file, a file with other plots I've done recently (so GPT can crib the style) and an empty file called `over_time.py`.
- Then I ask GPT to draw the scatterplot I want.
- I run the resulting script and share the error output with GPT so it can fix a small bug.
- I ask it to color the points for GPT-4 and GPT-3.5 family models differently, to better see trends within those model families.
- I add a PNG of the graph to the chat, so GPT can see the current graph and understand why I want it to move the point labels so they don't overlap the points.
- I work through a series of other small style changes, like changing fonts and the graph border.

In the end I have the graph, but I also have the python code in my repo.
So I can update this graph easily whenever I add new entries to the yaml data file.


## Aider chat transcript

<div class="chat-transcript" markdown="1">

> Aider v0.35.1-dev  
> Models: gpt-4o with diff edit format, weak model gpt-3.5-turbo  
> Added _data/edit_leaderboard.yml to the chat.  
> Added benchmark/over_time.py to the chat.  
> Added benchmark/plots.py to the chat.  

#### in over_time.py, draw a graph for each of the yaml entries with a `released` date. plot date on x, `pass_rate_2` on y and label with the `model` name. do a scatter plot. use colors/styles similar to the other graphs.  

To draw a scatter plot for each of the YAML entries with a `released` date, we need to:

1. Read the YAML file.
2. Extract the `released` date and `pass_rate_2` for each entry.
3. Plot the data using matplotlib.

Here are the changes:

benchmark/over_time.py
```python
<<<<<<< SEARCH
=======
import matplotlib.pyplot as plt
import yaml
from datetime import datetime

def plot_over_time(yaml_file):
    with open(yaml_file, 'r') as file:
        data = yaml.safe_load(file)

    dates = []
    pass_rates = []
    models = []

    for entry in data:
        if 'released' in entry and 'pass_rate_2' in entry:
            dates.append(datetime.strptime(entry['released'], '%Y-%m-%d'))
            pass_rates.append(entry['pass_rate_2'])
            models.append(entry['model'])

    plt.figure(figsize=(10, 6))
    plt.scatter(dates, pass_rates, c='blue', alpha=0.5)

    for i, model in enumerate(models):
        plt.annotate(model, (dates[i], pass_rates[i]), fontsize=8, alpha=0.75)

    plt.xlabel('Release Date')
    plt.ylabel('Pass Rate 2')
    plt.title('Model Performance Over Time')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Example usage
plot_over_time('_data/edit_leaderboard.yml')
>>>>>>> REPLACE
```

> Applied edit to benchmark/over_time.py  
> Commit 49ac9ca aider: Added scatter plot functionality for YAML entries with a `released` date and `pass_rate_2`.  

</div>
<div class="chat-transcript" markdown="1">

#### /run python benchmark/over_time.py  
> Traceback (most recent call last):
  File "/Users/gauthier/Projects/aider/benchmark/over_time.py", line 33, in <module>
    plot_over_time('_data/edit_leaderboard.yml')
  File "/Users/gauthier/Projects/aider/benchmark/over_time.py", line 15, in plot_over_time
    dates.append(datetime.strptime(entry['released'], '%Y-%m-%d'))
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: strptime() argument 1 must be str, not datetime.date  
> Add the output to the chat? y  
> Traceback (most recent call last):  
> File "/Users/gauthier/Projects/aider/benchmark/over_time.py", line 33, in <module>  
> plot_over_time('_data/edit_leaderboard.yml')  
> File "/Users/gauthier/Projects/aider/benchmark/over_time.py", line 15, in plot_over_time  
> dates.append(datetime.strptime(entry['released'], '%Y-%m-%d'))  
> ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  
> TypeError: strptime() argument 1 must be str, not datetime.date  

The error indicates that the `released` field in the YAML file is already a `datetime.date` object, so we don't need to parse it with `datetime.strptime`. We can directly use it in the plot.

Here are the changes:

benchmark/over_time.py
```python
<<<<<<< SEARCH
            dates.append(datetime.strptime(entry['released'], '%Y-%m-%d'))
=======
            dates.append(entry['released'])
>>>>>>> REPLACE
```

> Applied edit to benchmark/over_time.py  
> Commit af2f4b7 aider: Use the `released` field directly in the plot instead of parsing it with `datetime.strptime`.  

</div>
<div class="chat-transcript" markdown="1">

#### color the "gpt-4" models differently  

To color the "gpt-4" models differently, we need to modify the plotting code in `benchmark/over_time.py` to check for "gpt-4" in the model name and assign a different color.

Here are the changes:

benchmark/over_time.py
```python
<<<<<<< SEARCH
    plt.scatter(dates, pass_rates, c='blue', alpha=0.5)
=======
    colors = ['red' if 'gpt-4' in model else 'blue' for model in models]
    plt.scatter(dates, pass_rates, c=colors, alpha=0.5)
>>>>>>> REPLACE
```

This change will color the points red if the model name contains "gpt-4", otherwise, it will color them blue.

> Applied edit to benchmark/over_time.py  
> Commit 0d11357 aider: Color the "gpt-4" models differently.  

</div>
<div class="chat-transcript" markdown="1">

#### color the gpt-3.5 models a new color  

To color the "gpt-3.5" models a new color, we need to modify the plotting code in `benchmark/over_time.py` to check for "gpt-3.5" in the model name and assign a different color.

Here are the changes:

benchmark/over_time.py
```python
<<<<<<< SEARCH
    colors = ['red' if 'gpt-4' in model else 'blue' for model in models]
=======
    colors = ['red' if 'gpt-4' in model else 'green' if 'gpt-3.5' in model else 'blue' for model in models]
>>>>>>> REPLACE
```

> Applied edit to benchmark/over_time.py  
> Commit 85d9d84 aider: Color the "gpt-3.5" models green in the plotting code.  

</div>
<div class="chat-transcript" markdown="1">

#### use the colorscheme and fonts from the other graphs in plots.py  

To use the colorscheme and fonts from the graphs in `plots.py`, we need to:

1. Import the necessary settings from `plots.py`.
2. Apply these settings to the graph in `over_time.py`.

Here are the changes:

benchmark/over_time.py
```python
<<<<<<< SEARCH
import yaml
from datetime import datetime
=======
import yaml
from datetime import datetime
from matplotlib import rc
>>>>>>> REPLACE
```

benchmark/over_time.py
```python
<<<<<<< SEARCH
    plt.figure(figsize=(10, 6))
=======
    plt.rcParams["hatch.linewidth"] = 0.5
    plt.rcParams["hatch.color"] = "#444444"

    rc("font", **{"family": "sans-serif", "sans-serif": ["Helvetica"], "size": 10})

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.grid(axis="y", zorder=0, lw=0.2)
>>>>>>> REPLACE
```

benchmark/over_time.py
```python
<<<<<<< SEARCH
    plt.scatter(dates, pass_rates, c=colors, alpha=0.5)
=======
    ax.scatter(dates, pass_rates, c=colors, alpha=0.5)
>>>>>>> REPLACE
```

benchmark/over_time.py
```python
<<<<<<< SEARCH
        plt.annotate(model, (dates[i], pass_rates[i]), fontsize=8, alpha=0.75)

    plt.xlabel('Release Date')
    plt.ylabel('Pass Rate 2')
    plt.title('Model Performance Over Time')
    plt.grid(True)
    plt.tight_layout()
    plt.show()
=======
        ax.annotate(model, (dates[i], pass_rates[i]), fontsize=8, alpha=0.75)

    ax.set_xlabel('Release Date')
    ax.set_ylabel('Pass Rate 2')
    ax.set_title('Model Performance Over Time')
    plt.tight_layout()
    plt.savefig("tmp_over_time.svg")
    imgcat(fig)
>>>>>>> REPLACE
```

> Applied edit to benchmark/over_time.py  
> Commit 8d670f1 aider: Used the colorscheme and fonts from the graphs in `plots.py` in `over_time.py`.  


</div>
<div class="chat-transcript" markdown="1">

#### /add tmp_over_time.png  
> Added /Users/gauthier/Projects/aider/tmp_over_time.png to the chat  

#### make the labels not overlap the dots  

To make the labels not overlap the dots, we can adjust the position of the labels slightly using the `xytext` parameter in the `annotate` function.

Here are the changes:

benchmark/over_time.py
```python
<<<<<<< SEARCH
        ax.annotate(model, (dates[i], pass_rates[i]), fontsize=8, alpha=0.75)
=======
        ax.annotate(model, (dates[i], pass_rates[i]), fontsize=8, alpha=0.75,
                    xytext=(5, 5), textcoords='offset points')
>>>>>>> REPLACE
```

> Committing benchmark/over_time.py before applying edits.  
> Commit 49eb72c Updated image file format from SVG to PNG and added imgcat library for displaying the plot.  
> Applied edit to benchmark/over_time.py  
> Commit 75fa061 aider: Adjust the position of labels to prevent overlap with dots.  


</div>
<div class="chat-transcript" markdown="1">

#### make the dots bigger  

To make the dots bigger, we can adjust the `s` parameter in the `scatter` function, which controls the size of the dots.

Here are the changes:

benchmark/over_time.py
```python
<<<<<<< SEARCH
    ax.scatter(dates, pass_rates, c=colors, alpha=0.5)
=======
    ax.scatter(dates, pass_rates, c=colors, alpha=0.5, s=100)
>>>>>>> REPLACE
```

> Applied edit to benchmark/over_time.py  
> Commit a018fdf aider: Make the dots bigger.  

</div>
<div class="chat-transcript" markdown="1">

#### make the border of the graph thinner and lighter  

To make the border of the graph thinner and lighter, we can adjust the `spines` properties of the axes.

Here are the changes:

benchmark/over_time.py
```python
<<<<<<< SEARCH
    colors = ['red' if 'gpt-4' in model else 'green' if 'gpt-3.5' in model else 'blue' for model in models]
=======
    for spine in ax.spines.values():
        spine.set_edgecolor('#DDDDDD')
        spine.set_linewidth(0.5)

    colors = ['red' if 'gpt-4' in model else 'green' if 'gpt-3.5' in model else 'blue' for model in models]
>>>>>>> REPLACE
```

> Applied edit to benchmark/over_time.py  
> Commit 77ba518 aider: Made the border of the graph thinner and lighter by adjusting the `spines` properties of the axes.  

</div>
