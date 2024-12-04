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
      datasets: [
        {
          label: 'Solo model',
          data: filteredData.map(row => 
            (row.model === 'Qwen2.5 Coder 32B Instruct' || row.model === 'Sonnet (SOTA)') ? row.pass_rate_2 : null
          ),
          backgroundColor: 'rgba(75, 192, 192, 0.2)',  // Green
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1
        },
        {
          label: 'Architect + Editor',
          data: filteredData.map(row => 
            (row.model !== 'Qwen2.5 Coder 32B Instruct' && row.model !== 'Sonnet (SOTA)') ? row.pass_rate_2 : null
          ),
          backgroundColor: 'rgba(54, 162, 235, 0.2)',  // Blue
          borderColor: 'rgba(54, 162, 235, 1)',
          borderWidth: 1
        }
      ]
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
                }
              }
            },
            title: {
              display: true,
              text: 'Aider code editing benchmark results',
              font: {
                size: 16
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Percent completed correctly',
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
