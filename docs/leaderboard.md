
# Aider's LLM leaderboard

Aider works best with LLMs which are good at *editing* code, not just good at writing
code.
Aider works with the LLM to make changes to the existing code in your git repo,
so the LLM needs to be capable of reliably specifying how to edit code.

Aider uses a
[code editing benchmark](https://aider.chat/docs/benchmarks.html#the-benchmark)
to measure an LLM's code editing ability.
This table reports the results from a number of popular LLMs,
to help users select which models to use with aider.
While [aider can connect to almost any LLM](https://aider.chat/docs/llms.html)
it will work best with models that score well on the code editing benchmark.

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
    {% assign sorted = site.data.leaderboard | sort: 'second' | reverse %}
    {% for row in sorted %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px;">{{ row.second }}%</td>
        <td style="padding: 8px;"><code>{{ row.command }}</code></td>
        <td style="padding: 8px;">{{ row.format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>


## Edit format

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
[benchmark results CSV data file](https://github.com/paul-gauthier/aider/blob/main/_data/leaderboard.csv).
