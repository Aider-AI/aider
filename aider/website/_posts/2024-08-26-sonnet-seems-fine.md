---
title: Sonnet seems as good as ever
excerpt: Sonnet's score on the aider code editing benchmark has been stable since it launched.
highlight_image: /assets/linting.jpg
draft: true
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# Sonnet seems as good as ever

As part of developing aider, I benchmark the top LLMs regularly.
I have not noticed
any degradation in Claude 3.5 Sonnet's performance at code editing.
There has been a lot of speculation that Sonnet has been
dumbed-down, nerfed or otherwise performing worse lately.
Sonnet seems as good as ever, at least when accessed via
the API.

Here's a graph showing the performance of Claude 3.5 Sonnet over time.
It shows every benchmark run performed since Sonnet launched.
Benchmarks were performed for various reasons, usually
to evaluate the effects of small changes to aider's system prompts.
There is always some variance in benchmark results, typically +/- 1-2%
between runs with identical prompts.

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
        type: 'line',
        data: {
            datasets: [{
                label: 'Pass Rate 1',
                data: chartData.map(item => ({ x: item.x, y: item.y1 })),
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }, {
                label: 'Pass Rate 2',
                data: chartData.map(item => ({ x: item.x, y: item.y2 })),
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1
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
                        text: 'Pass Rate (%)'
                    }
                },
                x: {
                    type: 'time',
                    time: {
                        unit: 'day'
                    },
                    title: {
                        display: true,
                        text: 'Date'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Claude 3.5 Sonnet Performance Over Time'
                }
            }
        }
    });
});
</script>

This graph shows the performance of Claude 3.5 Sonnet on the 
[aider code editing benchmark](https://aider.chat/docs/leaderboards/)
over time. 'Pass Rate 1' represents the initial success rate, while 'Pass Rate 2' shows the success rate after a second attempt with a chance to fix testing errors. 


