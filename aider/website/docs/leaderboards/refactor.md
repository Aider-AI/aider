---
parent: Aider LLM Leaderboards
highlight_image: /assets/leaderboard.jpg
nav_order: 100
description: Quantitative benchmark of LLM code refactoring skill.
---


## Refactoring leaderboard

[Aider's refactoring benchmark](https://github.com/Aider-AI/refactor-benchmark) asks the LLM to refactor 89 large methods from large python classes. This is a more challenging benchmark, which tests the model's ability to output long chunks of code without skipping sections or making mistakes. It was developed to provoke and measure [GPT-4 Turbo's "lazy coding" habit](/2023/12/21/unified-diffs.html).

The refactoring benchmark requires a large context window to
work with large source files.
Therefore, results are available for fewer models.

<input type="text" id="editSearchInput" placeholder="Search..." style="width: 100%; max-width: 800px; margin: 10px auto; padding: 8px; display: block; border: 1px solid #ddd; border-radius: 4px;">

<table style="width: 100%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: center;">Percent completed correctly</th>
      <th style="padding: 8px; text-align: center;">Percent using correct edit format</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: center;">Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% assign refac_sorted = site.data.refactor_leaderboard | sort: 'pass_rate_1' | reverse %}
    {% for row in refac_sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px; text-align: center;">{{ row.pass_rate_1 }}%</td>
        <td style="padding: 8px; text-align: center;">{{ row.percent_cases_well_formed }}%</td>
        <td style="padding: 8px;"><code>{{ row.command }}</code></td>
        <td style="padding: 8px; text-align: center;">{{ row.edit_format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<canvas id="editChart" width="800" height="450" style="margin-top: 20px"></canvas>
<script src="https://unpkg.com/patternomaly/dist/patternomaly.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
{% assign data_source = refac_sorted %}
{% assign pass_rate_field = "pass_rate_1" %}
{% include leaderboard.js %}
</script>


<p class="post-date">
By Paul Gauthier,
last updated
<!--[[[cog
import subprocess
import datetime

files = [
    'aider/website/docs/leaderboards/refactor.md',
    'aider/website/_data/refactor_leaderboard.yml',
]

def get_last_modified_date(file):
    result = subprocess.run(['git', 'log', '-1', '--format=%ct', file], capture_output=True, text=True)
    if result.returncode == 0:
        timestamp = int(result.stdout.strip())
        return datetime.datetime.fromtimestamp(timestamp)
    return datetime.datetime.min

mod_dates = [get_last_modified_date(file) for file in files]
latest_mod_date = max(mod_dates)
cog.out(f"{latest_mod_date.strftime('%B %d, %Y.')}")
]]]-->
January 16, 2025.
<!--[[[end]]]-->
</p>
