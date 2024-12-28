---
title: o1 tops aider's new polyglot leaderboard
excerpt: o1 scores the top result on aider's new multi-language, more challenging coding benchmark.
highlight_image: /assets/o1-polyglot.jpg
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# o1 tops aider's new polyglot leaderboard
{: .no_toc }

<canvas id="editChart" width="800" height="450" style="margin-top: 20px"></canvas>

OpenAI's new o1 model with "high" reasoning effort
gets the top score on the
new 
[aider polyglot leaderboard](/docs/leaderboards/), significantly ahead of
other top LLMs.
The new polyglot benchmark uses many popular coding languages
and was designed to be 
*much more challenging* than aider's original
[code editing benchmark](/docs/leaderboards/edit.html).
This more clearly distinguishes 
the performance of
today's strongest coding models and
leaves headroom for future LLMs.

{: .note :}
See the main 
[aider leaderboard](https://aider.chat/docs/leaderboards/)
for benchmark results from more models.
This article only contains a snapshot
of results at the time of publication.

## The polyglot benchmark

Like aider's original code editing benchmark,
the new polyglot benchmark is based on Exercism
coding exercises.

The new polyglot benchmark:

- Contains coding problems in C++, Go, Java, JavaScript, Python and Rust. 
The old benchmark was solely based on Python exercises.
- Focuses on the *most difficult* 225 exercises out of the 697 that
Exercism provides for those languages.
The old benchmark simply included all 133 Python exercises,
regardless of difficulty.

## Motivation and goals

Aider's original code editing benchmark was 
saturating as the top scores approached and then surpassed 80%.
Sonnet's score of 84.2% was based on solving 112 of the 133
exercises, leaving only 21 unsolved exercises.
New champions were advancing the top score by
solving just 1-2 more problems than the previous record.
This made it hard to clearly 
measure the
difference in code editing skill between these top models.

Part of the problem is that many of the original
133 Python problems are very easy 
and provide
little challenge to today's frontier LLMs.
Models as old as GPT 3.5 Turbo were able to solve half of the
133 problems.
Such easy problems simply inflate the benchmark scores 
of modern LLMs without
providing any data about which models are better or worse.

The main goal for a new benchmark 
was to re-calibrate the scale so that
today's top coding LLMs 
would occupy a wide range of scores between about 5% and 50%.
This should leave headroom for future LLMs and
make it possible to
more clearly compare the relative performance of top models.

## Designing the polyglot benchmark

The new benchmark:

- Tests LLMs with more coding languages, to increase diversity and source a larger pool of problems.
- Includes just the most challenging coding problems and excludes easy problems that are solvable by most of today's top coding LLMs.
- Includes more total coding problems, to enable more granularity of comparison.

The new benchmark is based on Exercism coding problems
from 6 of the most popular programming languages:

- C++ 
- Go 
- Java
- JavaScript
- Python
- Rust

Exercism provides a total of 697 coding problems in those 6 languages.
A set of 7 of today's top coding models each attempted all 697 of
the Exercism problems:

- Sonnet
- Haiku
- o1 Mini
- DeepSeek
- GPT-4o
- Qwen 32B Coder Instruct
- GPT-4o Mini

Depending on the difficulty of the problems,
a different number of solutions were found by the collection of
7 models:

| Solutions<br>found | Number of<br>problems | Cumulative number<br>of problems |
|--------|-----------|------------|
| 0      | 66        | 66         |
| 1      | 61        | 127        |
| 2      | 50        | 177        |
| 3      | 48        | 225        |
| 4      | 53        | 278        |
| 5      | 71        | 349        |
| 6      | 90        | 439        |
| 7      | 258       | 697        |

In the table above, you can see that 258 of the problems were solved
by all 7 LLMs.
These problems are far too easy, and wouldn't be good choices for the new benchmark.
Instead, we need hard problems like the
66 that none of the 7 models were able to solve.

The new benchmark uses 
the 225 problems that were solved by 3 or fewer models.
This achieves a balance between hard and moderate problems,
and provides a large but not excessive total pool of problems.
It also represents a good diversity of coding languages:

| Language    | Problems |
|-------------|----------|
| C++         | 26       |
| Go          | 39       |
| Java        | 47       |
| JavaScript  | 49       |
| Python      | 34       |
| Rust        | 30       |
| **Total**   | **225**  |

## o1

OpenAI's new o1 model established a very strong
top score of 62% on the new benchmark.
This still leaves 86 problems of headroom for future models
to solve.
Given the incredible pace of recent advancements, it
will be interesting to see
how long it will take for this new benchmark to saturate.

## Benchmark problems

The 225 coding problems are available in the
[aider polyglot benchmark repo](https://github.com/Aider-AI/polyglot-benchmark)
on GitHub.



## Results

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
    {% assign edit_sorted = site.data.o1_polyglot_leaderboard | sort: 'pass_rate_2' | reverse %}
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

<script src="https://unpkg.com/patternomaly/dist/patternomaly.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
{% assign data_source = edit_sorted %}
{% assign pass_rate_field = "pass_rate_2" %}
{% assign highlight_model = "o1-2024" %}
{% include leaderboard.js %}
</script>
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
