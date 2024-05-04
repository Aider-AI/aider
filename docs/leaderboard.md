
# Aider's LLM leaderboards

Aider works best with LLMs which are good at *editing* code, not just good at writing
code.
Aider works with the LLM to make changes to the existing code in your git repo,
so the LLM needs to be capable of reliably specifying how to edit code.

Aider uses two benchmarks
to measure an LLM's code editing ability:

- The [code editing benchmark](https://aider.chat/docs/benchmarks.html#the-benchmark) asks the LLM to edit python source files to complete 133 Exercism exercises.
- The [refactoring benchmark](https://github.com/paul-gauthier/refactor-benchmark) asks the LLM to refactor large methods from a large python source file. This is a more challenging benchmark, which tests the model's ability to output long chunks of code without skipping sections.

These leaderboards report the results from a number of popular LLMs,
to help users select which models to use with aider.
While [aider can connect to almost any LLM](https://aider.chat/docs/llms.html)
it will work best with models that score well on the benchmarks.

## Code editing leaderboard

<table style="width: 90%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: center;">Percent correct</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: center;">Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% assign edit_sorted = site.data.edit_leaderboard | sort: 'second' | reverse %}
    {% for row in edit_sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px; text-align: center;">{{ row.second }}%</td>
        <td style="padding: 8px;"><code>{{ row.command }}</code></td>
        <td style="padding: 8px; text-align: center;">{{ row.format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<canvas id="editChart" width="800" height="450" style="margin-top: 20px"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('editChart').getContext('2d');
    var leaderboardData = {
      labels: [],
      datasets: [{
        label: 'Percent correct on code editing tasks',
        data: [],
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
      }]
    };

    {% for row in edit_sorted %}
      leaderboardData.labels.push('{{ row.model }}');
      leaderboardData.datasets[0].data.push({{ row.second }});
    {% endfor %}

    var leaderboardChart = new Chart(ctx, {
      type: 'bar',
      data: leaderboardData,
      options: {
        scales: {
          yAxes: [{
            scaleLabel: {
              display: true,
            },
            ticks: {
              beginAtZero: true
            }
          }]
        }
      }
    });
  });
</script>

## Code refactoring leaderboard

<table style="width: 90%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: center;">Percent correct</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: center;">Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% assign refac_sorted = site.data.refactor_leaderboard | sort: 'first' | reverse %}
    {% for row in refac_sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px; text-align: center;">{{ row.first }}%</td>
        <td style="padding: 8px;"><code>{{ row.command }}</code></td>
        <td style="padding: 8px; text-align: center;">{{ row.format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<canvas id="refacChart" width="800" height="450" style="margin-top: 20px"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    var ctx = document.getElementById('refacChart').getContext('2d');
    var leaderboardData = {
      labels: [],
      datasets: [{
        label: 'Percent correct on code refactoring tasks',
        data: [],
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
      }]
    };

    {% for row in refac_sorted %}
      leaderboardData.labels.push('{{ row.model }}');
      leaderboardData.datasets[0].data.push({{ row.first }});
    {% endfor %}

    var leaderboardChart = new Chart(ctx, {
      type: 'bar',
      data: leaderboardData,
      options: {
        scales: {
          yAxes: [{
            scaleLabel: {
              display: true,
            },
            ticks: {
              beginAtZero: true
            }
          }]
        }
      }
    });
  });
</script>



## Notes on the edit format

Aider uses different "edit formats" to collect code edits from different LLMs.
The "whole" format is the easiest for an LLM to use, but it uses a lot of tokens
and may limit how large a file can be edited.
Models which can use one of the diff formats are much more efficient,
using far fewer tokens.
Models that use a diff-like format are able to 
edit larger files with less cost and without hitting token limits.

Aider is configured to use the best edit format for the popular OpenAI and Anthropic models
and the [other models recommended on the LLM page](https://aider.chat/docs/llms.html).
For lesser known models aider will default to using the "whole" editing format
since it is the easiest format for an LLM to use.

## Contributing benchmark results

Contributions of benchmark results are welcome!
See the
[benchmark README](https://github.com/paul-gauthier/aider/blob/main/benchmark/README.md)
for information on running aider's code editing benchmark.
Submit results by opening a PR with edits to the
[benchmark results CSV data files](https://github.com/paul-gauthier/aider/blob/main/_data/).
