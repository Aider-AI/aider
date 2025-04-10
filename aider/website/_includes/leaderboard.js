document.addEventListener('DOMContentLoaded', function () {
  var ctx = document.getElementById('editChart').getContext('2d');
  const blueDiagonalPattern = pattern.draw('diagonal', 'rgba(54, 162, 235, 0.2)');
  const redDiagonalPattern = pattern.draw('diagonal', 'rgba(255, 99, 132, 0.2)');
  let displayedData = [];

  // Get highlight model from query string or Jekyll variable
  const urlParams = new URLSearchParams(window.location.search);
  const queryHighlight = urlParams.get('highlight');
  const HIGHLIGHT_MODEL = queryHighlight || '{{ highlight_model | default: "no no no" }}';

  var leaderboardData = {
    labels: [],
    datasets: [{
      label: 'Percent completed correctly',
      data: [],
      backgroundColor: function(context) {
        const row = allData[context.dataIndex];
        if (row && row.edit_format === 'whole') {
          return redDiagonalPattern; // Use red pattern for highlighted whole format
        }
        const label = leaderboardData.labels[context.dataIndex] || '';
        return (label && HIGHLIGHT_MODEL && label.toLowerCase().includes(HIGHLIGHT_MODEL.toLowerCase())) ? 'rgba(255, 99, 132, 0.2)' : 'rgba(54, 162, 235, 0.2)';
      },
      borderColor: function(context) {
        const label = context.chart.data.labels[context.dataIndex] || '';
        return (label && HIGHLIGHT_MODEL && label.toLowerCase().includes(HIGHLIGHT_MODEL.toLowerCase())) ? 'rgba(255, 99, 132, 1)' : 'rgba(54, 162, 235, 1)';
      },
      borderWidth: 1
    }, {
      label: 'Total Cost ($)',
      data: [],
      type: 'scatter',
      yAxisID: 'y1',
      backgroundColor: 'rgba(153, 102, 255, 1)',
      borderColor: '#fff',
      borderWidth: 1,
      pointRadius: 5,
      pointHoverRadius: 7
    }]
  };

  var allData = [];
  {% for row in data_source %}
    allData.push({
      model: '{{ row.model }}',
      pass_rate: {{ row[pass_rate_field] }},
      percent_cases_well_formed: {{ row.percent_cases_well_formed }},
      edit_format: '{{ row.edit_format | default: "diff" }}',
      total_cost: {{ row.total_cost | default: 0 }}
    });
  {% endfor %}

  function updateChart() {
    var selectedRows = document.querySelectorAll('tr.selected');
    var showAll = selectedRows.length === 0;

    displayedData = [];
    leaderboardData.labels = [];
    leaderboardData.datasets[0].data = [];
    leaderboardData.datasets[1].data = [];

    allData.forEach(function(row, index) {
      var rowElement = document.getElementById('edit-row-' + index);
      if (showAll) {
        rowElement.classList.remove('selected');
      }
      if (showAll || rowElement.classList.contains('selected')) {
        displayedData.push(row);
        leaderboardData.labels.push(row.model);
        leaderboardData.datasets[0].data.push(row.pass_rate);
        // Only include cost if it's not zero (placeholder for unknown)
        leaderboardData.datasets[1].data.push(row.total_cost > 0 ? row.total_cost : null);
      }
    });

    leaderboardChart.update();
    leaderboardChart.render();
  }

  // Update backgroundColor and borderColor for the main dataset based on displayedData
  leaderboardData.datasets[0].backgroundColor = function(context) {
    const row = displayedData[context.dataIndex];
    const label = leaderboardData.labels[context.dataIndex] || '';
    const isHighlighted = label && HIGHLIGHT_MODEL && label.toLowerCase().includes(HIGHLIGHT_MODEL.toLowerCase());

    if (isHighlighted) {
      if (row && row.edit_format === 'whole') return redDiagonalPattern;
      else return 'rgba(255, 99, 132, 0.2)';
    } else if (row && row.edit_format === 'whole') {
      return blueDiagonalPattern;
    } else {
      return 'rgba(54, 162, 235, 0.2)';
    }
  };

  var tableBody = document.querySelector('table tbody');
  allData.forEach(function(row, index) {
    var tr = tableBody.children[index];
    if (!tr) {
      // If the row doesn't exist, create it
      tr = document.createElement('tr');
      tableBody.appendChild(tr);
    }
    tr.id = 'edit-row-' + index;
    tr.style.cursor = 'pointer';
    tr.onclick = function() {
      this.classList.toggle('selected');
      updateChart();
    };
  });

  var leaderboardChart = new Chart(ctx, {
    type: 'bar',
    data: leaderboardData,
    options: {
      plugins: {
        legend: {
          display: {% if show_legend == false %}false{% else %}true{% endif %},
          labels: {
            generateLabels: function(chart) {
              return [
                {
                  text: 'Diff-like format',
                  fillStyle: 'rgba(54, 162, 235, 0.2)',
                  strokeStyle: 'rgba(54, 162, 235, 1)',
                  lineWidth: 1
                },
                {
                  text: 'Whole format',
                  fillStyle: blueDiagonalPattern,
                  strokeStyle: 'rgba(54, 162, 235, 1)',
                  lineWidth: 1
                },
                {
                  text: 'Total Cost ($)',
                  fillStyle: 'rgba(153, 102, 255, 1)',
                  strokeStyle: '#fff',
                  lineWidth: 1,
                  pointStyle: 'circle'
                }
              ];
            }
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const datasetLabel = context.dataset.label || '';
              const value = context.parsed.y;
              if (datasetLabel === 'Total Cost ($)') {
                return datasetLabel + ': $' + value.toFixed(2);
              }
              return datasetLabel + ': ' + value.toFixed(1) + '%';
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Percent completed correctly'
          }
        },
        y1: {
          beginAtZero: true,
          position: 'right',
          grid: {
            drawOnChartArea: false
          },
          title: {
            display: true,
            text: 'Total Cost ($)'
          }
        },
        x: {
          ticks: {
            autoSkip: false, // Prevent labels from being automatically skipped
            maxRotation: 90, // Allow labels to rotate up to 90 degrees
            minRotation: 0, 
            callback: function(value, index) {
              const label = this.getLabelForValue(value);
              if (label.length <= "claude-3-5-sonnet".length) {
                return label;
              }
              
              // Find all possible split positions
              const splitPositions = [];
              for (let i = 0; i < label.length; i++) {
                if (label[i] === '-' || label[i] === ' ') {
                  splitPositions.push(i);
                }
              }
              
              if (splitPositions.length === 0) {
                return label;
              }
              
              // Find split position closest to middle
              const middle = label.length / 2;
              const splitIndex = splitPositions.reduce((closest, current) => {
                return Math.abs(current - middle) < Math.abs(closest - middle) ? current : closest;
              });
              
              return [
                label.slice(0, splitIndex),
                label.slice(splitIndex + 1)
              ];
            }
          }
        }
      }
    }
  });

  updateChart();
  
  // Add search functionality for edit table
  document.getElementById('editSearchInput').addEventListener('keyup', function() {
    var searchWords = this.value.toLowerCase().split(' ').filter(word => word.length > 0);
    var tableBody = document.querySelector('table:first-of-type tbody');
    var rows = tableBody.getElementsByTagName('tr');
    
    displayedData = [];
    leaderboardData.labels = [];
    leaderboardData.datasets[0].data = [];
    leaderboardData.datasets[1].data = [];
    
    for (var i = 0; i < rows.length; i++) {
      var rowText = rows[i].textContent;
      if (searchWords.every(word => rowText.toLowerCase().includes(word))) {
        rows[i].style.display = '';
        displayedData.push(allData[i]);
        leaderboardData.labels.push(allData[i].model);
        leaderboardData.datasets[0].data.push(allData[i].pass_rate);
        // Only include cost if it's not zero (placeholder for unknown)
        leaderboardData.datasets[1].data.push(allData[i].total_cost > 0 ? allData[i].total_cost : null);
      } else {
        rows[i].style.display = 'none';
      }
    }
    leaderboardChart.update();
  });
});
