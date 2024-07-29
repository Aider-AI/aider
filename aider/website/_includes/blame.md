<canvas id="blameChart" width="800" height="450" style="margin-top: 20px"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/moment"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('blameChart').getContext('2d');
    var blameData = {
        datasets: [{
            label: 'Percent of Release Written by Aider',
            data: [
                {% for row in site.data.blame %}
                {
                    x: '{{ row.end_date }}',
                    y: {{ row.aider_percentage }},
                    label: '{{ row.end_tag }}'
                },
                {% endfor %}
            ],
            backgroundColor: 'rgba(54, 162, 235, 0.2)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }]
    };

    var blameChart = new Chart(ctx, {
        type: 'scatter',
        data: blameData,
        options: {
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day'
                    },
                    title: {
                        display: true,
                        text: 'Release date'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Percent of code written by aider'
                    },
                    beginAtZero: true,
                    max: 100
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.raw.label}: ${Math.round(context.raw.y)}%`;
                        }
                    }
                }
            }
        }
    });
});
</script>
