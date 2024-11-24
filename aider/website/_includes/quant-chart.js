document.addEventListener('DOMContentLoaded', function () {
  var ctx = document.getElementById('quantChart').getContext('2d');
  var allData = [];
  {% for row in site.data.quant %}
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
        label: 'Percent completed correctly',
        data: filteredData.map(row => row.pass_rate_2),
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        borderColor: 'rgba(54, 162, 235, 1)',
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
              display: false
            },
            title: {
              display: true,
              text: 'Aider code editing benchmark',
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
                  size: 14
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
              },
              title: {
                display: true,
                text: 'Provider: quantization',
                font: {
                  size: 14
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
  document.getElementById('quantSearchInput').addEventListener('keyup', function() {
    updateChart(this.value);
  });
});
