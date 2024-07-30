<canvas id="blameChart" width="800" height="450" style="margin-top: 20px"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/moment"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('blameChart').getContext('2d');
    var blameData = {
        datasets: [{
            label: 'Aider\'s Contribution to Each Release',
            data: [
                {% for row in site.data.blame %}
                {
                    x: '{{ row.end_date }}',
                    y: {{ row.aider_percentage }},
                    r: Math.sqrt({{ row.aider_total }}) * 1.5,
                    label: '{{ row.end_tag }}',
                    percentage: {{ row.aider_percentage }},
                    lines: {{ row.aider_total }}
                },
                {% endfor %}
            ],
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }]
    };

    var blameChart = new Chart(ctx, {
        type: 'bubble',
        data: blameData,
        options: {
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'month',
                        displayFormats: {
                            month: 'MMM YYYY'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Release date'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    },
                    min: moment('{{ site.data.blame | first | map: "end_date" | first }}').subtract(1, 'month'),
                    max: moment('{{ site.data.blame | last | map: "end_date" | first }}').add(1, 'month')
                },
                y: {
                    title: {
                        display: true,
                        text: 'Aider Contribution (% of code)'
                    },
                    beginAtZero: true,
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.raw.label}: ${Math.round(context.raw.percentage)}% (${context.raw.lines} lines)`;
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        generateLabels: function(chart) {
                            return [{
                                text: 'Bubble size: Lines of code contributed by aider',
                                fillStyle: 'rgba(54, 162, 235, 0.2)',
                                strokeStyle: 'rgba(54, 162, 235, 1)',
                                lineWidth: 1,
                                hidden: false,
                                index: 0
                            }];
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Aider\'s Contribution to Each Release',
                    font: {
                        size: 16
                    }
                }
            }
        }
    });
});
</script>
