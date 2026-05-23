---
title: Polyglot Leaderboard Chart
nav_order: 951
parent: Aider LLM Leaderboards
description: Interactive scatter plot of LLM performance vs cost on the polyglot benchmark.
---

# Polyglot Leaderboard Chart

Interactive scatter plot showing the relationship between cost and performance on Aider's polyglot coding benchmark.

<div style="margin: 20px 0;">
  <input type="text" id="chartSearchInput" placeholder="Search models..." style="padding: 8px; border: 1px solid #ddd; border-radius: 4px; width: 300px;">
</div>

<div style="width: 100%; max-width: 1000px; margin: 0 auto;">
  <canvas id="polyglotChart" width="800" height="600"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  // Data from polyglot_leaderboard.yml
  const allData = [];
  {% for row in site.data.polyglot_leaderboard %}
  allData.push({
    model: '{{ row.model }}',
    pass_rate: {{ row.pass_rate_2 }},
    total_cost: {{ row.total_cost | default: 0 }},
    edit_format: '{{ row.edit_format | default: "diff" }}',
    command: '{{ row.command }}',
    percent_cases_well_formed: {{ row.percent_cases_well_formed }}
  });
  {% endfor %}

  // Color mapping for edit formats
  const formatColors = {
    'diff': 'rgba(54, 162, 235, 0.7)',
    'diff-fenced': 'rgba(54, 162, 235, 0.9)',
    'editor-diff': 'rgba(54, 162, 235, 0.5)',
    'whole': 'rgba(255, 99, 132, 0.7)',
    'architect': 'rgba(75, 192, 192, 0.7)'
  };

  const formatBorderColors = {
    'diff': 'rgba(54, 162, 235, 1)',
    'diff-fenced': 'rgba(54, 162, 235, 1)',
    'editor-diff': 'rgba(54, 162, 235, 1)',
    'whole': 'rgba(255, 99, 132, 1)',
    'architect': 'rgba(75, 192, 192, 1)'
  };

  function createChart(data) {
    const ctx = document.getElementById('polyglotChart').getContext('2d');
    
    // Filter out models with zero cost for better visualization
    const chartData = data.map(row => ({
      x: row.total_cost,
      y: row.pass_rate,
      model: row.model,
      edit_format: row.edit_format,
      command: row.command,
      percent_cases_well_formed: row.percent_cases_well_formed
    }));

    return new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Models',
          data: chartData,
          backgroundColor: chartData.map(point => formatColors[point.edit_format] || 'rgba(128, 128, 128, 0.7)'),
          borderColor: chartData.map(point => formatBorderColors[point.edit_format] || 'rgba(128, 128, 128, 1)'),
          borderWidth: 2,
          pointRadius: 6,
          pointHoverRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            type: 'logarithmic',
            position: 'bottom',
            title: {
              display: true,
              text: 'Total Cost ($)'
            },
            min: 0.01,
            ticks: {
              callback: function(value) {
                if (value === 0) return '$0';
                if (value < 1) return '$' + value.toFixed(2);
                if (value < 10) return '$' + value.toFixed(1);
                return '$' + Math.round(value);
              }
            }
          },
          y: {
            title: {
              display: true,
              text: 'Pass Rate (%)'
            },
            min: 0,
            max: 100
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              title: function(context) {
                return context[0].raw.model;
              },
              label: function(context) {
                const point = context.raw;
                return [
                  `Pass Rate: ${point.y}%`,
                  `Cost: $${point.x.toFixed(2)}`,
                  `Edit Format: ${point.edit_format}`,
                  `Well Formed: ${point.percent_cases_well_formed}%`
                ];
              }
            }
          }
        },
        onClick: function(event, elements) {
          if (elements.length > 0) {
            const point = elements[0];
            const data = point.element.$context.raw;
            console.log('Clicked model:', data.model);
          }
        }
      }
    });
  }

  function updateChart(filterText) {
    const filteredData = allData.filter(row => 
      row.model.toLowerCase().includes(filterText.toLowerCase())
    );
    
    // Destroy existing chart and create new one
    if (window.polyglotChart) {
      window.polyglotChart.destroy();
    }
    window.polyglotChart = createChart(filteredData);
  }

  // Initialize chart
  document.addEventListener('DOMContentLoaded', function() {
    window.polyglotChart = createChart(allData);
    
    // Add search functionality
    const searchInput = document.getElementById('chartSearchInput');
    searchInput.addEventListener('input', function() {
      updateChart(this.value);
    });
  });
</script>

<div style="margin-top: 20px;">
  <h3>Legend</h3>
  <div style="display: flex; flex-wrap: wrap; gap: 15px; margin-top: 10px;">
    <div style="display: flex; align-items: center;">
      <div style="width: 12px; height: 12px; background-color: rgba(54, 162, 235, 0.7); border: 2px solid rgba(54, 162, 235, 1); border-radius: 50%; margin-right: 8px;"></div>
      <span>Diff formats</span>
    </div>
    <div style="display: flex; align-items: center;">
      <div style="width: 12px; height: 12px; background-color: rgba(255, 99, 132, 0.7); border: 2px solid rgba(255, 99, 132, 1); border-radius: 50%; margin-right: 8px;"></div>
      <span>Whole file</span>
    </div>
    <div style="display: flex; align-items: center;">
      <div style="width: 12px; height: 12px; background-color: rgba(75, 192, 192, 0.7); border: 2px solid rgba(75, 192, 192, 1); border-radius: 50%; margin-right: 8px;"></div>
      <span>Architect</span>
    </div>
  </div>
</div>

<div style="margin-top: 20px; font-size: 14px; color: #666;">
  <p><strong>Note:</strong> Cost axis uses logarithmic scale. Models with $0 cost are positioned at $0.01 for visibility. Hover over points for detailed information.</p>
</div>
