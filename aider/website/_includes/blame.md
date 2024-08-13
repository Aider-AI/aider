<canvas id="blameChart" width="800" height="450" style="margin-top: 20px"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/moment"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('blameChart').getContext('2d');
    var blameData = {
        labels: [{% for row in site.data.blame %}'{{ row.end_tag }}',{% endfor %}],
        datasets: [{
            label: 'Aider\'s Contribution to Each Release',
            data: [{% for row in site.data.blame %}{ x: '{{ row.end_tag }}', y: {{ row.aider_percentage }}, lines: {{ row.aider_total }} },{% endfor %}],
            backgroundColor: 'rgba(54, 162, 235, 0.8)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }]
    };

    var blameChart = new Chart(ctx, {
        type: 'bar',
        data: blameData,
        options: {
            scales: {
                x: {
                    type: 'category',
                    title: {
                        display: true,
                        text: 'Version'
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Aider Contribution (% of code)'
                    },
                    beginAtZero: true
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            var label = context.dataset.label || '';
                            var value = context.parsed.y || 0;
                            var lines = context.raw.lines || 0;
                            return `${label}: ${Math.round(value)}% (${lines} lines)`;
                        }
                    }
                },
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        generateLabels: function(chart) {
                            return [{
                                text: 'Y-axis is percent of code, bubble size is lines of code',
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
