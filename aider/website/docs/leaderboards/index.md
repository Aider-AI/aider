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

<input type="text" id="editSearchInput" placeholder="Search..." style="width: 100%; max-width: 800px; margin: 10px auto; padding: 8px; display: block; border: 1px solid #ddd; border-radius: 4px;">

<div id="view-mode-toggle" style="margin-bottom: 10px; text-align: center;">
  <button data-mode="all" class="mode-button active">All</button>
  <button data-mode="select" class="mode-button">Select</button>
  <button data-mode="selected" class="mode-button">Selected</button>
  <button id="clear-selection-button" style="display: none; margin-left: 10px;">Clear Selection</button>
</div>

<table style="width: 100%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; width: 40px;"></th> <!-- Toggle/Select column -->
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

  /* Style for the toggle buttons */
  #view-mode-toggle .mode-button {
    padding: 5px 10px;
    border: 1px solid #ccc;
    background-color: #f8f9fa;
    cursor: pointer;
  }
  #view-mode-toggle .mode-button:first-child {
    border-top-left-radius: 4px;
    border-bottom-left-radius: 4px;
  }
  /* Adjust last-of-type selector to account for the clear button potentially being the last */
  #view-mode-toggle .mode-button:nth-last-child(2) { /* Targets the 'Selected' button */
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
    border-left: none; /* If buttons are adjacent */
  }
  #view-mode-toggle .mode-button.active {
    background-color: #e9ecef;
    font-weight: bold;
  }
  #view-mode-toggle .mode-button:not(:first-child):not(.active) {
      border-left: none; /* Avoid double borders */
  }
  #clear-selection-button {
      padding: 5px 10px;
      border: 1px solid #ccc;
      background-color: #f8f9fa;
      cursor: pointer;
      border-radius: 4px;
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

</style>

<script>
document.addEventListener('DOMContentLoaded', function() {
  let currentMode = 'all'; // 'all', 'select', 'selected'
  let selectedRows = new Set(); // Store indices of selected rows

  const modeToggleButtonContainer = document.getElementById('view-mode-toggle');
  const modeButtons = modeToggleButtonContainer.querySelectorAll('.mode-button');
  const clearSelectionButton = document.getElementById('clear-selection-button');
  const allMainRows = document.querySelectorAll('tr[id^="main-row-"]');
  const allDetailsRows = document.querySelectorAll('tr[id^="details-"]');
  const searchInput = document.getElementById('editSearchInput');

  function applySearchFilter() {
    const searchTerm = searchInput.value.toLowerCase();
    allMainRows.forEach(row => {
      const textContent = row.textContent.toLowerCase();
      const detailsRow = document.getElementById(row.id.replace('main-row-', 'details-'));
      const matchesSearch = textContent.includes(searchTerm);

      if (matchesSearch) {
        row.classList.remove('hidden-by-search');
        if (detailsRow) detailsRow.classList.remove('hidden-by-search');
      } else {
        row.classList.add('hidden-by-search');
        if (detailsRow) detailsRow.classList.add('hidden-by-search');
      }
    });
    // After applying search filter, re-apply view mode filter
    updateTableView(currentMode);
  }


  function updateTableView(mode) {
    currentMode = mode; // Update global state

    // Update button active states
    modeButtons.forEach(btn => {
      if (btn.dataset.mode === mode) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Show/hide clear selection button
    clearSelectionButton.style.display = (mode === 'select' || mode === 'selected') && selectedRows.size > 0 ? 'inline-block' : 'none';

    allMainRows.forEach(row => {
      const rowIndex = row.querySelector('.row-selector')?.dataset.rowIndex;
      const toggleButton = row.querySelector('.toggle-details');
      const selectorCheckbox = row.querySelector('.row-selector');
      const detailsRow = document.getElementById(`details-${rowIndex}`);
      const isSelected = selectedRows.has(rowIndex);

      // Reset visibility classes before applying mode logic
      row.classList.remove('hidden-by-mode');
      if (detailsRow) detailsRow.classList.remove('hidden-by-mode');

      // Apply mode-specific logic
      switch (mode) {
        case 'all':
          toggleButton.style.display = 'inline-block';
          selectorCheckbox.style.display = 'none';
          row.classList.toggle('row-selected', isSelected); // Keep visual selection indication
          // Hide details row unless it was explicitly opened (handled by toggle listener)
          if (detailsRow && toggleButton.textContent === '▶') {
              detailsRow.style.display = 'none';
          }
          break;
        case 'select':
          toggleButton.style.display = 'none';
          selectorCheckbox.style.display = 'inline-block';
          selectorCheckbox.checked = isSelected;
          row.classList.toggle('row-selected', isSelected);
          // Always hide details row in select mode
          if (detailsRow) detailsRow.style.display = 'none';
          break;
        case 'selected':
          toggleButton.style.display = 'inline-block';
          selectorCheckbox.style.display = 'none';
          if (isSelected) {
            row.classList.add('row-selected'); // Ensure selected class is present
            // Hide details row unless it was explicitly opened
             if (detailsRow && toggleButton.textContent === '▶') {
                detailsRow.style.display = 'none';
            }
          } else {
            row.classList.add('hidden-by-mode');
            row.classList.remove('row-selected'); // Remove selection class if not selected
            if (detailsRow) detailsRow.classList.add('hidden-by-mode'); // Hide details too
          }
          break;
      }

      // Ensure rows hidden by search remain hidden regardless of mode
      if (row.classList.contains('hidden-by-search')) {
          row.style.display = 'none';
          if (detailsRow) detailsRow.style.display = 'none';
      } else if (!row.classList.contains('hidden-by-mode')) {
          // Make row visible if not hidden by search or mode
          row.style.display = ''; // Or 'table-row' if needed, but '' usually works
      } else {
          // Row is hidden by mode, ensure it's hidden
          row.style.display = 'none';
          if (detailsRow) detailsRow.style.display = 'none';
      }


    });
  }


  // --- Existing Initializations ---
  // Add percentage ticks
  const percentCells = document.querySelectorAll('.bar-cell:not(.cost-bar-cell)');
  percentCells.forEach(cell => {
    // Add ticks at 0%, 10%, 20%, ..., 100%
    for (let i = 0; i <= 100; i += 10) {
      const tick = document.createElement('div');
      tick.className = 'percent-tick';
      tick.style.left = `${i}%`;
      cell.appendChild(tick);
    }
  });

  // Process cost bars
  const costBars = document.querySelectorAll('.cost-bar');
  costBars.forEach(bar => {
    const cost = parseFloat(bar.dataset.cost);
    const maxCost = parseFloat(bar.dataset.maxCost);
 
    if (cost > 0 && maxCost > 0) {
      // Use log10(1 + x) for scaling. Adding 1 handles potential cost=0 and gives non-zero logs for cost > 0.
      const logCost = Math.log10(1 + cost);
      const logMaxCost = Math.log10(1 + maxCost);
 
      if (logMaxCost > 0) {
        // Calculate percentage relative to the log of max cost
        const percent = (logCost / logMaxCost) * 100;
        // Clamp percentage between 0 and 100
        bar.style.width = Math.max(0, Math.min(100, percent)) + '%';
      } else {
        // Handle edge case where maxCost is 0 (so logMaxCost is 0)
        // If maxCost is 0, cost must also be 0, handled below.
        // If maxCost > 0 but logMaxCost <= 0 (e.g., maxCost is very small), set width relative to cost?
        // For simplicity, setting to 0 if logMaxCost isn't positive.
        bar.style.width = '0%';
      }
    } else {
      // Set width to 0 if cost is 0 or negative
      bar.style.width = '0%';
    }
  });

  // Calculate and add cost ticks dynamically
  const costCells = document.querySelectorAll('.cost-bar-cell');
  if (costCells.length > 0) {
    // Find the max cost from the first available cost bar's data attribute
    const firstCostBar = document.querySelector('.cost-bar');
    const maxCost = parseFloat(firstCostBar?.dataset.maxCost || '1'); // Use 1 as fallback

    if (maxCost > 0) {
      const logMaxCost = Math.log10(1 + maxCost);

      if (logMaxCost > 0) { // Ensure logMaxCost is positive to avoid division by zero or negative results
        const tickValues = [];
        // Generate ticks starting at $0, then $10, $20, $30... up to maxCost
        tickValues.push(0); // Add tick at base (0 position)
        for (let tickCost = 10; tickCost <= maxCost; tickCost += 10) {
          tickValues.push(tickCost);
        }

        // Calculate percentage positions for each tick on the log scale
        const tickPercentages = tickValues.map(tickCost => {
          const logTickCost = Math.log10(1 + tickCost);
          return (logTickCost / logMaxCost) * 100;
        });

        // Add tick divs to each cost cell
        costCells.forEach(cell => {
          const costBar = cell.querySelector('.cost-bar');
          // Use optional chaining and provide '0' as fallback if costBar or dataset.cost is missing
          const cost = parseFloat(costBar?.dataset?.cost || '0');

          // Only add ticks if the cost is actually greater than 0
          if (cost > 0) {
            // Clear existing ticks if any (e.g., during updates, though not strictly needed here)
            // cell.querySelectorAll('.cost-tick').forEach(t => t.remove());

            tickPercentages.forEach(percent => {
              // Ensure percentage is within valid range
              if (percent >= 0 && percent <= 100) {
                const tick = document.createElement('div');
                tick.className = 'cost-tick';
                tick.style.left = `${percent}%`;
                cell.appendChild(tick);
              }
            });
          }
        });
      }
    }
  }

  // Add toggle functionality for details
  const toggleButtons = document.querySelectorAll('.toggle-details');
  toggleButtons.forEach(button => {
    button.addEventListener('click', function() {
      const targetId = this.getAttribute('data-target');
      const targetRow = document.getElementById(targetId);
      if (targetRow) {
        const isVisible = targetRow.style.display !== 'none';
        targetRow.style.display = isVisible ? 'none' : 'table-row';
        this.textContent = isVisible ? '▶' : '▼'; // Use Unicode triangles
      }
    });
  });

});
</script>
 
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
