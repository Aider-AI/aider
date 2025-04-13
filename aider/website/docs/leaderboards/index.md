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
      <th style="padding: 8px; text-align: center;">Percent correct</th>
      <th style="padding: 8px; text-align: center;">Percent using correct edit format</th>
      <th style="padding: 8px; text-align: center;">Cost</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: center;">Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% assign max_cost = 0 %}
    {% for row in site.data.polyglot_leaderboard %}
      {% if row.total_cost > max_cost %}
        {% assign max_cost = row.total_cost %}
      {% endif %}
    {% endfor %}
    {% if max_cost == 0 %}{% assign max_cost = 1 %}{% endif %}
    {% assign edit_sorted = site.data.polyglot_leaderboard | sort: 'pass_rate_2' | reverse %}
    {% for row in edit_sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;"><span>{{ row.model }}</span></td>
        <td class="bar-cell">
          <div class="bar-viz" style="width: {{ row.pass_rate_2 }}%; background-color: {% if row.pass_rate_2 >= 80 %}rgba(40, 167, 69, 0.3){% elsif row.pass_rate_2 >= 50 %}rgba(255, 193, 7, 0.3){% else %}rgba(220, 53, 69, 0.3){% endif %}; border-right: 1px solid {% if row.pass_rate_2 >= 80 %}rgba(40, 167, 69, 0.5){% elsif row.pass_rate_2 >= 50 %}rgba(255, 193, 7, 0.5){% else %}rgba(220, 53, 69, 0.5){% endif %};"></div>
          <span>{{ row.pass_rate_2 }}%</span>
        </td>
        <td class="bar-cell">
          <div class="bar-viz" style="width: {{ row.percent_cases_well_formed }}%; background-color: {% if row.percent_cases_well_formed >= 80 %}rgba(40, 167, 69, 0.3){% elsif row.percent_cases_well_formed >= 50 %}rgba(255, 193, 7, 0.3){% else %}rgba(220, 53, 69, 0.3){% endif %}; border-right: 1px solid {% if row.percent_cases_well_formed >= 80 %}rgba(40, 167, 69, 0.5){% elsif row.percent_cases_well_formed >= 50 %}rgba(255, 193, 7, 0.5){% else %}rgba(220, 53, 69, 0.5){% endif %};"></div>
          <span>{{ row.percent_cases_well_formed }}%</span>
        </td>
        {% assign cost_percent = row.total_cost | times: 100.0 | divided_by: max_cost %}
        <td class="bar-cell">
          <div class="bar-viz" style="width: {{ cost_percent }}%; background-color: {% if cost_percent >= 80 %}rgba(111, 66, 193, 0.3){% elsif cost_percent >= 50 %}rgba(111, 66, 193, 0.2){% else %}rgba(111, 66, 193, 0.1){% endif %}; border-right: 1px solid {% if cost_percent >= 80 %}rgba(111, 66, 193, 0.5){% elsif cost_percent >= 50 %}rgba(111, 66, 193, 0.4){% else %}rgba(111, 66, 193, 0.3){% endif %};"></div>
          <span>{% if row.total_cost == 0 %}?{% else %}${{ row.total_cost | times: 1.0 | round: 2 }}{% endif %}</span>
        </td>
        <td style="padding: 8px;"><span><code>{{ row.command }}</code></span></td>
        <td style="padding: 8px; text-align: center;"><span>{{ row.edit_format }}</span></td>
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
{% assign highlight_model = "xxxxxx" %}
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
  td:nth-child(5), td:nth-child(6) { /* Command and Edit Format columns */
    font-size: 12px;
  }
  
  /* Hide command and edit format columns on mobile */
  @media screen and (max-width: 767px) {
    th:nth-child(5), td:nth-child(5), /* Command column */
    th:nth-child(6), td:nth-child(6) { /* Edit format column */
      display: none;
    }
  }
  .bar-cell {
    position: relative; /* Positioning context for the bar */
    padding: 8px;
    text-align: center; /* Keep text centered */
    overflow: hidden; /* Prevent bar from overflowing cell boundaries if needed */
  }
  .bar-viz {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 0; /* Behind the text */
    height: 60%; /* Bar height */
    margin: auto 0; /* Vertical centering */
    border-radius: 0 2px 2px 0; /* Slightly rounded end corners */
    /* Width and colors are set inline via style attribute */
  }
  .bar-cell span {
     position: relative; /* Needed to stack above the absolute positioned bar */
     z-index: 1; /* Ensure text is above the bar */
     /* Optional: Add padding or background for better readability */
     /* background-color: rgba(255, 255, 255, 0.7); */
     /* padding: 0 2px; */
     /* border-radius: 2px; */
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
April 12, 2025.
<!--[[[end]]]-->
</p>
