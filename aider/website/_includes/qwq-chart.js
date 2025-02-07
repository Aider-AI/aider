document.addEventListener('DOMContentLoaded', function () {
  var ctx = document.getElementById('qwqChart').getContext('2d');
  var allData = [];
  {% for row in site.data.qwq %}
    allData.push({
      model: '{{ row.model }}',
      pass_rate_2: {{ row.pass_rate_2 }}
    });
  {% endfor %}

  // Sort data by pass_rate_2 in descending order
  allData.sort((a, b) => b.pass_rate_2 - a.pass_rate_2);

  var chart;
  
  function updateChart(filterText) {
    var filteredData = allData.filter(row => 
      row.model.toLowerCase().includes(filterText.toLowerCase())
    );
    
    var chartData = {
      labels: filteredData.map(row => row.model),
      datasets: [{
        data: filteredData.map(row => row.pass_rate_2),
        backgroundColor: filteredData.map(row => 
          (row.model === 'Qwen2.5 Coder 32B-I' || row.model === 'Sonnet (SOTA)' || row.model === 'o1-mini' || row.model === 'o1-preview' || row.model === 'QwQ') 
            ? 'rgba(75, 192, 192, 0.2)'   // Green for solo models
            : 'rgba(54, 162, 235, 0.2)'   // Blue for architect+editor
        ),
        borderColor: filteredData.map(row => 
          (row.model === 'Qwen2.5 Coder 32B-I' || row.model === 'Sonnet (SOTA)' || row.model === 'o1-mini' || row.model === 'o1-preview' || row.model === 'QwQ')
            ? 'rgba(75, 192, 192, 1)'     // Green border for solo models
            : 'rgba(54, 162, 235, 1)'     // Blue border for architect+editor
        ),
        borderWidth: 1
      }]
    };

    if (chart) {
      chart.data = chartData;
      chart.update();
    } else {
      chart = new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: {
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: {
                font: {
                  size: 14
                },
                generateLabels: function(chart) {
                  return [
                    {
                      text: 'Solo model',
                      fillStyle: 'rgba(75, 192, 192, 0.2)',
                      strokeStyle: 'rgba(75, 192, 192, 1)',
                      lineWidth: 1,
                      fontColor: '#666'
                    },
                    {
                      text: 'Architect + Editor',
                      fillStyle: 'rgba(54, 162, 235, 0.2)',
                      strokeStyle: 'rgba(54, 162, 235, 1)',
                      lineWidth: 1,
                      fontColor: '#666'
                    }
                  ];
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Aider code editing benchmark (%)',
                font: {
                  size: 18
                }
              },
              ticks: {
                font: {
                  size: 16
                }
              }
            },
            x: {
              ticks: {
                font: {
                  size: 16
                },
                callback: function(value, index) {
                  const label = this.getLabelForValue(value);
                  if (label.includes(" + ")) {
                    const parts = label.split(" + ");
                    return [parts[0] + " +", parts[1]];
                  }
                  return label;
                }
              }
            }
          }
        }
      });
    }
  }

  // Initial chart render
  updateChart('');

  // Connect search input to chart filtering
  document.getElementById('qwqSearchInput').addEventListener('keyup', function() {
    updateChart(this.value);
  });
});
