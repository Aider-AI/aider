<canvas id="passRateChart" width="800" height="400" style="margin-bottom: 20px"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('passRateChart').getContext('2d');
    
    var yamlData = {{ site.data.code-in-json | jsonify }};
    
    var models = [...new Set(yamlData.map(item => item.model))].sort();
    var editFormats = [...new Set(yamlData.map(item => item.edit_format))];
    
    var datasets = editFormats.map(format => ({
        label: format,
        data: models.map(model => {
            var items = yamlData.filter(d => d.model === model && d.edit_format === format);
            if (items.length === 0) return null;
            var average = items.reduce((sum, item) => sum + item.pass_rate_1, 0) / items.length;
            return parseFloat(average.toFixed(1));
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
                        text: 'Pass Rate (%, average of 5 runs)'
                    },
                    max: 70
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Pass rate by model and code wrapping strategy',
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
                                label += context.parsed.y.toFixed(1) + '%';
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
                            ctx.fillText(data.toFixed(1) + '%', bar.x, bar.y - 5);
                        }
                    });
                });
            }
        }]
    };

    function createStripedCanvas(isStrict) {
        const patternCanvas = document.createElement('canvas');
        const patternContext = patternCanvas.getContext('2d');
        const size = 10;
        patternCanvas.width = size;
        patternCanvas.height = size;

        patternContext.fillStyle = 'rgba(255, 99, 132, 0.8)';
        patternContext.fillRect(0, 0, size, size);

        if (isStrict) {
            patternContext.strokeStyle = 'rgba(255, 255, 255, 0.8)';
            patternContext.lineWidth = 0.75;
            patternContext.beginPath();
            patternContext.moveTo(0, 0);
            patternContext.lineTo(size, size);
            patternContext.stroke();
        }

        return patternCanvas;
    }

    new Chart(ctx, config);
});

function createStripedCanvas(isStrict) {
    const patternCanvas = document.createElement('canvas');
    const patternContext = patternCanvas.getContext('2d');
    const size = 10;
    patternCanvas.width = size;
    patternCanvas.height = size;

    patternContext.fillStyle = 'rgba(255, 99, 132, 0.8)';
    patternContext.fillRect(0, 0, size, size);

    if (isStrict) {
        patternContext.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        patternContext.lineWidth = 0.75;
        patternContext.beginPath();
        patternContext.moveTo(0, 0);
        patternContext.lineTo(size, size);
        patternContext.stroke();
    }

    return patternCanvas;
}
</script>
