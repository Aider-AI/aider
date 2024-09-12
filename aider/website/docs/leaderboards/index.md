---
highlight_image: /assets/leaderboard.jpg
nav_order: 950
description: Quantitative benchmarks of LLM code editing skill.
---


# Aider LLM Leaderboards
{: .no_toc }

Aider works best with LLMs which are good at *editing* code, not just good at writing
code.
To evaluate an LLM's editing skill, aider uses a pair of benchmarks that
assess a model's ability to consistently follow the system prompt
to successfully edit code.

The leaderboards below report the results from a number of popular LLMs.
While [aider can connect to almost any LLM](/docs/llms.html),
it works best with models that score well on the benchmarks.

See the following sections for benchmark
results and additional information:
- TOC
{:toc}

## Code editing leaderboard

[Aider's code editing benchmark](/docs/benchmarks.html#the-benchmark) asks the LLM to edit python source files to complete 133 small coding exercises
from Exercism. 
This measures the LLM's coding ability, and whether it can
write new code that integrates into existing code.
The model also has to successfully apply all its changes to the source file without human intervention.

<table style="width: 100%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: center;">Percent completed correctly</th>
      <th style="padding: 8px; text-align: center;">Percent using correct edit format</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: center;">Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% assign edit_sorted = site.data.edit_leaderboard | sort: 'pass_rate_2' | reverse %}
    {% for row in edit_sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px; text-align: center;">{{ row.pass_rate_2 }}%</td>
        <td style="padding: 8px; text-align: center;">{{ row.percent_cases_well_formed }}%</td>
        <td style="padding: 8px;"><code>{{ row.command }}</code></td>
        <td style="padding: 8px; text-align: center;">{{ row.edit_format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

{% include leaderboard_graph.html 
  chart_id="editChart" 
  data=edit_sorted 
  row_prefix="edit-row" 
  pass_rate_key="pass_rate_2"
%}
<style>
  tr.selected {
    color: #0056b3;
  }
  table {
    table-layout: fixed;
  }
  td, th {
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
  td:nth-child(3), td:nth-child(4) {
    font-size: 12px;
  }
</style>

## Code refactoring leaderboard

[Aider's refactoring benchmark](https://github.com/paul-gauthier/refactor-benchmark) asks the LLM to refactor 89 large methods from large python classes. This is a more challenging benchmark, which tests the model's ability to output long chunks of code without skipping sections or making mistakes. It was developed to provoke and measure [GPT-4 Turbo's "lazy coding" habit](/2023/12/21/unified-diffs.html).

The refactoring benchmark requires a large context window to
work with large source files.
Therefore, results are available for fewer models.

<table style="width: 100%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 14px;">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: center;">Percent completed correctly</th>
      <th style="padding: 8px; text-align: center;">Percent using correct edit format</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: center;">Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% assign refac_sorted = site.data.refactor_leaderboard | sort: 'pass_rate_1' | reverse %}
    {% for row in refac_sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px; text-align: center;">{{ row.pass_rate_1 }}%</td>
        <td style="padding: 8px; text-align: center;">{{ row.percent_cases_well_formed }}%</td>
        <td style="padding: 8px;"><code>{{ row.command }}</code></td>
        <td style="padding: 8px; text-align: center;">{{ row.edit_format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

{% include leaderboard_graph.html 
  chart_id="refacChart" 
  data=refac_sorted 
  row_prefix="refac-row" 
  pass_rate_key="pass_rate_1"
%}


## LLM code editing skill by model release date

[![connecting to many LLMs](/assets/models-over-time.svg)](https://aider.chat/assets/models-over-time.svg)


## Notes on benchmarking results

The key benchmarking results are:

- **Percent completed correctly** - Measures what percentage of the coding tasks that the LLM completed successfully. To complete a task, the LLM must solve the programming assignment *and* edit the code to implement that solution.
- **Percent using correct edit format** - Measures the percent of coding tasks where the LLM complied with the edit format specified in the system prompt. If the LLM makes edit mistakes, aider will give it feedback and ask for a fixed copy of the edit. The best models can reliably conform to the edit format, without making errors.


## Notes on the edit format

Aider uses different "edit formats" to collect code edits from different LLMs.
The "whole" format is the easiest for an LLM to use, but it uses a lot of tokens
and may limit how large a file can be edited.
Models which can use one of the diff formats are much more efficient,
using far fewer tokens.
Models that use a diff-like format are able to 
edit larger files with less cost and without hitting token limits.

Aider is configured to use the best edit format for the popular OpenAI and Anthropic models
and the [other models recommended on the LLM page](/docs/llms.html).
For lesser known models aider will default to using the "whole" editing format
since it is the easiest format for an LLM to use.

## Contributing benchmark results

Contributions of benchmark results are welcome!
See the
[benchmark README](https://github.com/paul-gauthier/aider/blob/main/benchmark/README.md)
for information on running aider's code editing benchmarks.
Submit results by opening a PR with edits to the
[benchmark results data files](https://github.com/paul-gauthier/aider/blob/main/website/_data/).


<p class="post-date">
By Paul Gauthier,
last updated
<!--[[[cog
import subprocess
import datetime

files = [
    'aider/website/docs/leaderboards/index.md',
    'aider/website/_data/edit_leaderboard.yml',
    'aider/website/_data/refactor_leaderboard.yml'
]

def get_last_modified_date(file):
    result = subprocess.run(['git', 'log', '-1', '--format=%ct', file], capture_output=True, text=True)
    if result.returncode == 0:
        timestamp = int(result.stdout.strip())
        return datetime.datetime.fromtimestamp(timestamp)
    return datetime.datetime.min

mod_dates = [get_last_modified_date(file) for file in files]
latest_mod_date = max(mod_dates)
cog.out(f"{latest_mod_date.strftime('%B %d, %Y.')}")
]]]-->
September 12, 2024.
<!--[[[end]]]-->
</p>
