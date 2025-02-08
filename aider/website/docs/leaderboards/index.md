---
highlight_image: /assets/leaderboard.jpg
nav_order: 950
description: Quantitative benchmarks of LLM code editing skill.
has_children: true
---


# Aider LLM Leaderboards

Aider works best with LLMs which are good at *editing* code, not just good at writing
code.
To evaluate an LLM's editing skill, aider uses benchmarks that
assess a model's ability to consistently follow the system prompt
to successfully edit code.

The leaderboards report the results from a number of popular LLMs.
While [aider can connect to almost any LLM](/docs/llms.html),
it works best with models that score well on the benchmarks.


## Polyglot leaderboard

[Aider's polyglot benchmark](https://aider.chat/2024/12/21/polyglot.html#the-polyglot-benchmark) 
asks the LLM to edit source files to complete 225 coding exercises
from Exercism. 
It contains exercises in many popular programming languages:
C++, Go, Java, JavaScript, Python and Rust.
The 225 exercises were purposely selected to be the *hardest*
that Exercism offered in those languages, to provide
a strong coding challenge to LLMs.

This benchmark measures the LLM's coding ability in popular languages, 
and whether it can
write new code that integrates into existing code.
The model also has to successfully apply all its changes to the source file without human intervention.

<input type="text" id="editSearchInput" placeholder="Search..." style="width: 100%; max-width: 800px; margin: 10px auto; padding: 8px; display: block; border: 1px solid #ddd; border-radius: 4px;">

<table style="width: 100%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: center;">Percent completed correctly</th>
      <th style="padding: 8px; text-align: center;">Percent using correct edit format</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: center;">Edit format</th>
      <th style="padding: 8px; text-align: center;">Total Cost</th>
    </tr>
  </thead>
  <tbody>
    {% assign edit_sorted = site.data.polyglot_leaderboard | sort: 'pass_rate_2' | reverse %}
    {% for row in edit_sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px; text-align: center;">{{ row.pass_rate_2 }}%</td>
        <td style="padding: 8px; text-align: center;">{{ row.percent_cases_well_formed }}%</td>
        <td style="padding: 8px;"><code>{{ row.command }}</code></td>
        <td style="padding: 8px; text-align: center;">{{ row.edit_format }}</td>
        <td style="padding: 8px; text-align: center;">{% if row.total_cost == 0 %}?{% else %}${{ row.total_cost | times: 1.0 | round: 2 }}{% endif %}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

### Aider polyglot benchmark results

<canvas id="editChart" width="800" height="450" style="margin-top: 20px"></canvas>
<script src="https://unpkg.com/patternomaly/dist/patternomaly.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
{% assign data_source = edit_sorted %}
{% assign pass_rate_field = "pass_rate_2" %}
{% assign highlight_model = "xxxxxxxxxxx" %}
{% include leaderboard.js %}
</script>
<style>
  tr.selected {
    color: #0056b3;
  }
  table {
    table-layout: fixed;
  }
  td, th {
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
  td:nth-child(3), td:nth-child(4) {
    font-size: 12px;
  }
</style>




<p class="post-date">
By Paul Gauthier,
last updated
<!--[[[cog
import subprocess
import datetime

files = [
    'aider/website/docs/leaderboards/index.md',
    'aider/website/_data/polyglot_leaderboard.yml',
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
January 31, 2025.
<!--[[[end]]]-->
</p>
