
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

<table style="width: 90%; max-width: 800px; margin: auto; border-collapse: collapse; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
  <thead style="background-color: #f2f2f2;">
    <tr>
      <th style="padding: 8px; text-align: left;">Model</th>
      <th style="padding: 8px; text-align: left;">Percent correct</th>
      <th style="padding: 8px; text-align: left;">Command</th>
      <th style="padding: 8px; text-align: left;">Edit format</th>
    </tr>
  </thead>
  <tbody>
    {% for row in site.data.leaderboard %}
      <tr style="border-bottom: 1px solid #ddd;">
        <td style="padding: 8px;">{{ row.model }}</td>
        <td style="padding: 8px;">{{ row.second }}%</td>
        <td style="padding: 8px;"><pre style="overflow-x: auto; white-space: pre-wrap;">{{ row.command }}</pre></td>
        <td style="padding: 8px;">{{ row.format }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>


## Edit format


Aider uses different "edit formats" to collect code edits from different LLMs:

- `whole` is a "whole file" editing format, where the model edits a file by returning a full new copy of the file with any changes included.
- `diff` is a more efficient diff style format, where the model specifies blocks of code to search and replace in order to made changes to files.
- `diff-fenced` is similar to diff, but fences the entire diff block including the filename.
- `udiff` is the most efficient editing format, where the model returns unified diffs to apply changes to the file.

Different models work best with different editing formats.
Aider is configured to use the best edit format for the popular OpenAI and Anthropic models
and the [other models recommended on the LLM page](https://aider.chat/docs/llms.html).

For lesser known models aider will default to using the "whole" editing format
since it is the easiest format for an LLM to use.
But it is also the least efficient, requiring the model to output the
entire source file for every set of changes.
This can raise costs and cause errors with LLMs that have smaller
context window sizes.

All of the other diff-like edit formats are much more efficient with their use of tokens.


