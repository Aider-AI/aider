---
highlight_image: /assets/leaderboard.jpg
nav_order: 950
description: Quantitative benchmarks of LLM code editing skill.
has_children: true
---


# Aider LLM Leaderboards

Aider excels with LLMs skilled at *editing* code, not just writing it.
These benchmarks evaluate an LLM's ability to follow instructions and edit code successfully without
human intervention.
Aider works best with high-scoring models, though it [can connect to almost any LLM](/docs/llms.html).


## Polyglot leaderboard

[Aider's polyglot benchmark](https://aider.chat/2024/12/21/polyglot.html#the-polyglot-benchmark) tests LLMs on 225 challenging Exercism coding exercises across C++, Go, Java, JavaScript, Python, and Rust.

<div id="controls-container" style="display: flex; align-items: center; max-width: 800px; margin: 10px auto; gap: 10px;">
  <input type="text" id="editSearchInput" placeholder="Search..." style="flex-grow: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
  <div id="view-mode-toggle" style="display: inline-flex; border: 1px solid #ccc; border-radius: 4px;">
    <button id="mode-view-btn" class="mode-button active" data-mode="view" style="padding: 8px 12px; border: none; border-radius: 3px 0 0 3px; cursor: pointer; font-size: 14px; line-height: 1.5;">View</button>
    <button id="mode-select-btn" class="mode-button" data-mode="select" style="padding: 8px 12px; border: none; background-color: #f8f9fa; border-radius: 0 3px 3px 0; cursor: pointer; border-left: 1px solid #ccc; font-size: 14px; line-height: 1.5;">Select</button>
  </div>
</div>

<table style="width: 100%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; width: 40px; text-align: center; vertical-align: middle;">
        <input type="checkbox" id="select-all-checkbox" style="display: none; cursor: pointer; vertical-align: middle;">
      </th> <!-- Header checkbox added here -->
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: center;">Percent correct</th>
      <th style="padding: 8px; text-align: center;">Cost (log scale)</th>
      <th style="padding: 8px; text-align: left;">Command</th>
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
    {% for row in edit_sorted %} {% comment %} Add loop index for unique IDs {% endcomment %}
      {% assign row_index = forloop.index0 %}
      <tr id="main-row-{{ row_index }}">
        <td style="padding: 8px; text-align: center; vertical-align: middle;">
          <button class="toggle-details" data-target="details-{{ row_index }}" style="background: none; border: none; cursor: pointer; font-size: 16px; padding: 0; vertical-align: middle;">▶</button>
          <input type="checkbox" class="row-selector" data-row-index="{{ row_index }}" style="display: none; cursor: pointer; vertical-align: middle;">
        </td>
        <td style="padding: 8px;"><span>{{ row.model }}</span></td>
        <td class="bar-cell">
          <div class="bar-viz" style="width: {{ row.pass_rate_2 }}%; background-color: rgba(40, 167, 69, 0.3); border-right: 1px solid rgba(40, 167, 69, 0.5);"></div>
          <span>{{ row.pass_rate_2 }}%</span>
        </td>
        <td class="bar-cell cost-bar-cell">
          {% if row.total_cost > 0 %}
          <div class="bar-viz cost-bar" data-cost="{{ row.total_cost }}" data-max-cost="{{ max_cost }}" style="width: 0%; background-color: rgba(13, 110, 253, 0.3); border-right: 1px solid rgba(13, 110, 253, 0.5);"></div>
          {% endif %}
          {% assign rounded_cost = row.total_cost | times: 1.0 | round: 2 %}
          <span>{% if row.total_cost == 0 or rounded_cost == 0.00 %}?{% else %}${{ rounded_cost }}{% endif %}</span>
        </td>
        <td style="padding: 8px;"><span><code>{{ row.command }}</code></span></td>
      </tr>
      <tr class="details-row" id="details-{{ row_index }}" style="display: none; background-color: #f9f9f9;">
        <td colspan="5" style="padding: 15px; border-bottom: 1px solid #ddd;">
          <ul style="margin: 0; padding-left: 20px; list-style: none; border-bottom: 1px solid #ddd;">
            {% for pair in row %}
              {% if pair[1] != "" and pair[1] != nil %}
                <li><strong>{{ pair[0] | replace: '_', ' ' | capitalize }}:</strong>
                  {% if pair[0] == 'command' %}<code>{{ pair[1] }}</code>{% else %}{{ pair[1] }}{% endif %}
                </li>
              {% endif %}
            {% endfor %}
          </ul>
        </td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<style>
  tr.selected {
    color: #0056b3;
  }
  table {
    table-layout: fixed;
  }
  thead {
    border-top: 1px solid #ddd; /* Add top border to header */
  }
  td, th {
    border: none; /* Remove internal cell borders */
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
  td:nth-child(5) { /* Command column */
    font-size: 12px; /* Keep font size adjustment for command column if desired, or remove */
  }

  /* Hide command column on mobile */
  @media screen and (max-width: 767px) {
    th:nth-child(5), td:nth-child(5) { /* Command column */
      display: none;
    }
  }

  /* --- Control Styles --- */
  #controls-container {
    margin-bottom: 20px; /* Add some space below controls */
  }

  #editSearchInput, #view-mode-select {
    padding: 8px 12px; /* Consistent padding */
    border: 1px solid #ccc; /* Slightly softer border */
    border-radius: 4px;
    font-size: 14px; /* Match table font size */
    height: 38px; /* Match height */
    box-sizing: border-box; /* Include padding/border in height */
  }


  .bar-cell {
    position: relative; /* Positioning context for the bar */
    padding: 8px;
    /* text-align: center; Removed */
    overflow: hidden; /* Prevent bar from overflowing cell boundaries if needed */
  }
  .cost-bar-cell {
    background-image: none; /* Remove default gradient for cost cells */
  }
  .percent-tick, .cost-tick {
    position: absolute;
    top: 50%;
    transform: translateY(10px);
    height: 8px; /* Short tick */
    width: 1px;
    background-color: rgba(170, 170, 170, 0.5); 
    z-index: 2; /* Above the bar but below the text */
  }
  .bar-viz {
    position: absolute;
    left: 0;
    top: 50%; /* Position at the middle of the cell */
    transform: translateY(-50%); /* Center the bar vertically */
    z-index: 1; /* Above background, below ticks and text */
    height: 36px;
    border-radius: 0 2px 2px 0; /* Slightly rounded end corners */
    /* Width and colors are set inline via style attribute */
  }
  .bar-cell span {
     position: absolute; /* Position relative to the cell */
     left: 5px; /* Position slightly inside the left edge */
     top: 50%; /* Center vertically */
     transform: translateY(-50%); /* Adjust vertical centering */
     z-index: 3; /* Ensure text is above everything else */
     background-color: rgba(255, 255, 255, 0.7); /* Semi-transparent white background */
     padding: 0 4px; /* Add padding around the text */
     border-radius: 3px; /* Rounded corners for the text background */
     font-size: 14px; /* Adjust font size for the numbers */
  }
  .toggle-details {
    color: #888; /* Make toggle symbol more subtle */
    transition: color 0.2s; /* Smooth transition on hover */
  }


  /* Style for selected rows */
  tr.row-selected > td {
    background-color: #e7f3ff; /* Example light blue highlight */
  }

  /* Ensure checkbox is vertically aligned if needed */
  .row-selector {
    vertical-align: middle;
  }

  /* Hide rows not matching the filter */
  tr.hidden-by-mode {
      display: none !important; /* Use important to override other display styles if necessary */
  }
  tr.hidden-by-search {
      display: none !important;
  }

  /* --- Mode Toggle Button Styles --- */
  #view-mode-toggle {
    height: 38px; /* Match input height */
    box-sizing: border-box;
  }
  .mode-button {
    transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out;
  }
  .mode-button:not(.active) {
    background-color: #f8f9fa; /* Light grey background */
    color: #495057; /* Dark grey text */
  }
  .mode-button:not(.active):hover {
    background-color: #e2e6ea; /* Slightly darker grey on hover */
  }

  /* Style for highlighted rows in view mode */
  tr.view-highlighted > td {
    background-color: #f0f0f0; /* Example light grey highlight */
  }
</style>

{% include leaderboard_table.js %}

<p class="post-date" style="margin-top: 20px;">
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
