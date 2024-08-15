<div id="syntaxErrorsContainer" style="position: relative; height: 0; padding-bottom: 50%; margin-bottom: 20px;">
    <canvas id="syntaxErrorsChart" style="position: absolute; width: 100%; height: 100%;"></canvas>
</div>

<script>
document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('syntaxErrorsChart').getContext('2d');
    
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

    var config = {
        type: 'bar',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
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
                        text: 'Total syntactic errors from 5 runs'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Syntactic errors by model and code wrapping strategy',
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

    // Adjust chart height based on screen width
    function adjustChartHeight() {
        var container = document.getElementById('syntaxErrorsContainer');
        if (window.innerWidth < 600) {
            container.style.paddingBottom = '75%'; // Increase height on small screens
        } else {
            container.style.paddingBottom = '50%'; // Default height
        }
    }

    // Call the function initially and on window resize
    adjustChartHeight();
    window.addEventListener('resize', adjustChartHeight);

    new Chart(ctx, config);
});
</script>
