---
title: Sonnet seems as good as ever
excerpt: Sonnet's score on the aider code editing benchmark has been stable since it launched.
highlight_image: /assets/sonnet-seems-fine.jpg
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Sonnet seems as good as ever

Recently there has been a lot of speculation that Sonnet has been
dumbed-down, nerfed or is otherwise performing worse.
Sonnet seems as good as ever, when performing the
[aider code editing benchmark](/docs/benchmarks.html#the-benchmark)
via the API.

Below is a graph showing the performance of Claude 3.5 Sonnet over time.
It shows every clean, comparable benchmark run performed since Sonnet launched.
Benchmarks were performed for various reasons, usually
to evaluate the effects of small changes to aider's system prompts.

The graph shows variance, but no indication of a noteworthy
degradation.
There is always some variance in benchmark results, typically +/- 2%
between runs with identical prompts.

It's worth noting that these results would not capture any changes
made to Anthropic web chat's use of Sonnet.

<div class="chart-container" style="position: relative; height:400px; width:100%">
    <canvas id="sonnetPerformanceChart"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/moment@2.29.4/moment.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-moment@1.0.1/dist/chartjs-adapter-moment.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    var ctx = document.getElementById('sonnetPerformanceChart').getContext('2d');
    var sonnetData = {{ site.data.sonnet-fine | jsonify }};

    var chartData = sonnetData.map(item => ({
        x: moment(item.date).toDate(),
        y1: item.pass_rate_1,
        y2: item.pass_rate_2
    })).sort((a, b) => a.x - b.x);

    new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Pass Rate 1',
                data: chartData.map(item => ({ x: item.x, y: item.y1 })),
                backgroundColor: 'rgb(75, 192, 192)',
                pointRadius: 5,
                pointHoverRadius: 7
            }, {
                label: 'Pass Rate 2',
                data: chartData.map(item => ({ x: item.x, y: item.y2 })),
                backgroundColor: 'rgb(255, 99, 132)',
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Pass Rate (%)',
                        font: {
                            size: 14
                        }
                    },
                    ticks: {
                        font: {
                            size: 12
                        }
                    }
                },
                x: {
                    type: 'time',
                    time: {
                        unit: 'day'
                    },
                    title: {
                        display: true,
                        text: 'Date',
                        font: {
                            size: 14
                        }
                    },
                    ticks: {
                        font: {
                            size: 12
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Claude 3.5 Sonnet Performance Over Time',
                    font: {
                        size: 18
                    }
                },
                legend: {
                    labels: {
                        font: {
                            size: 14
                        }
                    }
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
        }
    });
});
</script>

> This graph shows the performance of Claude 3.5 Sonnet on 
[aider's code editing benchmark](/docs/benchmarks.html#the-benchmark)
> over time. 'Pass Rate 1' represents the initial success rate, while 'Pass Rate 2' shows the success rate after a second attempt with a chance to fix testing errors. 
> The 
> [aider LLM code editing leaderboard](https://aider.chat/docs/leaderboards/)
> ranks models based on Pass Rate 2.

