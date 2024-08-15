<style>
    .chart-container {
        position: relative;
        width: 100%;
        max-width: 800px;
        margin: 0 auto;
    }
</style>

<div class="chart-container">
    <canvas id="syntaxErrorsChart"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('syntaxErrorsChart').getContext('2d');
    var chartContainer = document.querySelector('.chart-container');
    
    var yamlData = {{ site.data.code-in-json | jsonify }};
    
    var models = [...new Set(yamlData.map(item => item.model))].sort();
    var editFormats = [...new Set(yamlData.map(item => item.edit_format))];
    
    var datasets = editFormats.map(format => ({
        label: format,
        data: models.map(model => {
            var items = yamlData.filter(d => d.model === model && d.edit_format === format);
            if (items.length === 0) return null;
            var totalErrors = items.reduce((sum, item) => sum + item.syntax_errors + item.indentation_errors, 0);
            return totalErrors;
        }),
        backgroundColor: function(context) {
            const format = context.dataset.label;
            if (format === 'Markdown') {
                return 'rgba(54, 162, 235, 0.8)';
            } else if (format.startsWith('JSON')) {
                const ctx = context.chart.ctx;
                const gradient = ctx.createPattern(createStripedCanvas(format === 'JSON (strict)'), 'repeat');
                return gradient;
            } else {
                return 'rgba(75, 192, 192, 0.8)';
            }
        },
    }));

    var data = {
        labels: models,
        datasets: datasets
    };

    function getAspectRatio() {
        var width = chartContainer.offsetWidth;
        // Gradually change aspect ratio from 2 (landscape) to 1 (square)
        return Math.max(1, Math.min(2, width / 300));
    }

    var config = {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: getAspectRatio(),
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Model'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Total syntax errors from 5 runs'
                    },
                    max: 35
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Syntax errors by model and code wrapping strategy',
                    font: {
                        size: 16
                    }
                },
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y;
                            }
                            return label;
                        }
                    }
                }
            }
        },
        plugins: [{
            afterDraw: function(chart) {
                var ctx = chart.ctx;
                chart.data.datasets.forEach(function(dataset, i) {
                    var meta = chart.getDatasetMeta(i);
                    meta.data.forEach(function(bar, index) {
                        var data = dataset.data[index];
                        if (data !== null) {
                            ctx.fillStyle = '#000000';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'bottom';
                            ctx.fillText(data, bar.x, bar.y - 5);
                        }
                    });
                });
            }
        }]
    };

    var chart = new Chart(ctx, config);

    function resizeChart() {
        chart.options.aspectRatio = getAspectRatio();
        chart.resize();
    }

    window.addEventListener('resize', resizeChart);

    // Initial resize to set correct size
    resizeChart();
});
</script>
