---
title: LLM code editing skill over time
excerpt: A comparison of LLM code editing skill based on the release dates of the models.
---
# LLM code editing skill over time

<canvas id="scatterPlot" width="800" height="450" style="margin-top: 20px"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('scatterPlot').getContext('2d');
    var scatterData = {
      datasets: [{
        label: 'Model Performance',
        data: [
          {% for row in site.data.edit_leaderboard %}
            {% if row.released %}
              {
                x: new Date('{{ row.released }}'),
                y: {{ row.pass_rate_2 }},
                label: '{{ row.model }}'
              },
            {% endif %}
          {% endfor %}
        ],
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
        pointRadius: 5,
        pointHoverRadius: 7
      }]
    };

    var scatterChart = new Chart(ctx, {
      type: 'scatter',
      data: scatterData,
      options: {
        scales: {
          xAxes: [{
            type: 'time',
            time: {
              unit: 'month',
              tooltipFormat: 'll'
            },
            scaleLabel: {
              display: true,
              labelString: 'Release Date'
            }
          }],
          yAxes: [{
            scaleLabel: {
              display: true,
              labelString: 'Pass Rate 2 (%)'
            },
            ticks: {
              beginAtZero: true
            }
          }]
        },
        tooltips: {
          callbacks: {
            label: function(tooltipItem, data) {
              var label = data.datasets[tooltipItem.datasetIndex].data[tooltipItem.index].label || '';
              return label + ': (' + tooltipItem.xLabel + ', ' + tooltipItem.yLabel + '%)';
            }
          }
        }
      }
    });
  });
</script>

