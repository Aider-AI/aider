---
title: QwQ is a code architect, not an editor
excerpt: QwQ is reasoning model like o1, and needs to be used as an architect with another model as editor.
highlight_image: /assets/qwq.jpg
draft: false
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# QwQ is a code architect, not an editor
{: .no_toc }

<canvas id="qwqChart" width="800" height="500" style="margin: 20px 0"></canvas>

QwQ 32B Preview is a "reasoning" model, which spends a lot of tokens thinking before
rendering a final response.
This is similar to OpenAI's o1 models, which are most effective with aider
[when paired as an architect with a traditional LLM as an editor](https://aider.chat/2024/09/26/architect.html).
In this mode, the reasoning model acts as an "architect" to propose a solution to the
coding problem without regard for how to actually make edits to the source files.
The "editor" model receives that proposal, and focuses solely on how to
edit the existing source code to implement it.

Used alone without being paired with an editor, 
QwQ was unable to comply with even the simplest 
[editing format](https://aider.chat/docs/more/edit-formats.html).
It was not able to reliably edit source code files.
As a result, QwQ's solo score on the benchmark was quite underwhelming
(and far worse than the o1 models performing solo).

QwQ is based on
Qwen 2.5 Coder 32B Instruct,
and does better when paired with it as an architect + editor combo.
Though this provided only a modest benchmark improvement over just using Qwen alone,
and comes with a fairly high cost in terms of latency.
Each request must wait for QwQ to return all its thinking text
and the final solution proposal.
And then one must wait for Qwen to turn that large
response into actual file edits.

Pairing QwQ with other sensible editor models performed the same or worse than
just using Qwen 2.5 Coder 32B Instruct alone.

QwQ+Qwen seems to be the best way to use QwQ, achieving a score of 74%.
That is well below the
SOTA results for this benchmark: Sonnet alone scores 84%, and
o1-preview + o1-mini as architect + editor scores 85%.


## QwQ specific editing formats

I spent some time experimenting with a variety of custom editing formats
for QwQ.
In particular, I tried to parse the QwQ response and discard the long
sections of "thinking" and retain only the "final" solution.
None of this custom work seemed to translate 
into any significant improvement in the benchmark results.


## Results

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
{% include qwq-chart.js %}
</script>

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
    {% assign qwq_sorted = site.data.qwq | sort: 'pass_rate_2' | reverse %}
    {% for row in qwq_sorted %}
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

<script>
document.getElementById('qwqSearchInput').addEventListener('keyup', function() {
    var input = this.value.toLowerCase();
    var rows = document.querySelectorAll('tbody tr');
    
    rows.forEach(function(row) {
        var text = row.textContent.toLowerCase();
        if(text.includes(input)) {
            row.style.display = '';
            row.classList.add('selected');
        } else {
            row.style.display = 'none';
            row.classList.remove('selected');
        }
    });
});
</script>

## Open source model caveats

As discussed in a recent blog post,
[details matter with open source models](https://aider.chat/2024/11/21/quantization.html).
For clarity, new benchmark runs for this article were
performed against OpenRouter's endpoints for
QwQ 32B Preview and Qwen 2.5 Coder 32B Instruct.
For the other models, the benchmark was direct to their providers' APIs.

Having recently done extensive testing of OpenRouter's Qwen 2.5 Coder 32B Instruct endpoint,
it seems reliable.
The provider Mancer was blocked due to the small context window it provides.

For QwQ 32B Preview, Fireworks was blocked because of its small context window.
