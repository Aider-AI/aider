---
title: Aider is SOTA for both the main SWE Bench and SWE Bench Lite
excerpt: Aider sets SOTA for the main SWE Bench, after recently setting SOTA for the Lite version.
highlight_image: /assets/swe_bench.jpg
draft: true
---

# Aider is SOTA for both the main SWE Bench and SWE Bench Lite
 
Aider scored 18.8%
on the main
[SWE Bench benchmark](https://www.swebench.com),
achieving a state-of-the-art result. 
The current top leaderboard entry is 13.8%
from Amazon Q Developer Agent.

This is in addition to
[aider's SOTA result on the easier SWE Bench Lite](https://aider.chat/2024/05/22/swe-bench-lite.html)
that was reported last week.

[![SWE Bench results](/assets/swe_bench.svg)](https://aider.chat/assets/swe_bench.svg)

Aider was benchmarked on 570 of the 2294 SWE Bench problems.
These are the same [randomly selected 570 problems](https://github.com/CognitionAI/devin-swebench-results/tree/main/output_diffs) that
[Devin used in their evalulation](https://www.cognition.ai/post/swe-bench-technical-report).
Please see the [references](#references)
for more details on the data presented in this chart.

## Interactive, not agentic

Aider achieved this result mainly through its existing features that focus on static code analysis, reliable LLM code editing, and pragmatic UX for AI pair programming.
Aider intentionally has quite limited and narrow "agentic behavior"
to avoid long delays, high token costs
and the need for users to repeatedly code review incorrect solutions.
It's also worth noting that aider currently does not use
RAG, vector search, tools or give the LLM access to search the web
or unilaterally execute code.

Aider is first and foremost an interactive tool for engineers to get real work done in
real code bases using a chat interface.
Aider provides a pair programming UX where users can ask for a change
and see the edits performed in real-time.
Aider can also offer additional help like fixing lint or test errors,
but the user is always in full interactive control.
This lets them quickly steer misunderstandings back on course and
avoid wasting time and token costs.


## Benchmark methodology

For the benchmark, 
aider with GPT-4o was launched in each problem's git repository
with the problem statement
submitted as the opening chat message from "the user."
After that aider runs as normal, with the following modifications:

- Aider's suggestions were always accepted without user approval.
- A simple harness was used to retry the SWE Bench problem if aider produced code that wasn't *plausibly correct*.
Plausibly correct means that aider reported that it had successfully edited the repo
without causing syntax errors or breaking any *pre-existing* tests.
- If the solution isn't plausible, the harness launches aider to try again from scratch,
this time using Claude 3 Opus.
- If no plausible solution is found after those two tries, the harness picks the "most plausible" solution with the fewest edit/lint/test problems.

It's important to be clear that
*aider and the benchmark harness
only had access to the pre-existing tests in each problem's repo*.
The held out "acceptance tests" were *only* used
after benchmarking to compute statistics on which problems aider
correctly resolved.

This is the same methodology
that was used for [aider's recent SOTA result on SWE Bench Lite](https://aider.chat/2024/05/22/swe-bench-lite.html).
The only difference is that at most two tries were attempted instead of six,
due to the increased token costs involved in this benchmark.
The SWE Bench problems are more difficult and involve edits to
more than one source file,
which increased the cost of solving each problem.
Further, aider was benchmarked on 570 SWE Bench problems,
versus only 300 Lite problems,
adding another factor of ~two to the costs.

For a detailed discussion of the methodology, please see the
[article about aider's SWE Bench Lite results](https://aider.chat/2024/05/22/swe-bench-lite.html).
The [aider SWE Bench repository on GitHub](https://github.com/paul-gauthier/aider-swe-bench) also contains
the harness and reporting code used for the benchmarks.

The benchmarking process was similar to how a developer might use aider to
resolve a GitHub issue:

- They could launch aider in their repo with the command below, which
tells aider they want to accept every suggestion
and to use pytest to run tests.
  - `aider --yes --test-cmd pytest`
- They could start the chat by pasting in the URL or text of a GitHub issue.
Aider will pull in the URL's content and then try and solve the issue.
- If aider doesn't produce code that lints and tests clean, the user might decide to revert the changes and try again, maybe using aider with a different LLM this time.
[Aider is tightly integrated with git](https://aider.chat/docs/faq.html#how-does-aider-use-git),
so it's always easy to revert AI changes that don't pan out.

## Aider with GPT-4o alone was SOTA

Running the benchmark harness
only using aider with GPT-4o to find plausible solutions with a single attempt
achieved a score of 17.0%.
This was itself a state-of-the-art result, before being surpassed by the main
result being reported here
that used aider with both GPT-4o & Opus.

## Aider with GPT-4o & Opus

The benchmark harness started by running aider with GPT-4o once to try
and solve the problem. If
no plausible solution was found, it then used aider with Opus
once to try and solve the problem.

The table below breaks down the proposed solutions that
were found for the 570 problems.
A proposed solution is either:

- A plausible solution where
aider reported no outstanding errors from editing, linting and testing.
- Or, the "most plausible" solution generated by either attempt, with the
[fewest outstanding editing, linting or testing errors](https://aider.chat/2024/05/22/swe-bench-lite.html#finding-a-plausible-solution).

The table also provides details on the 107 solutions that were ultimately
verified as correctly resolving their issue.

| Attempt | Agent |Number&nbsp;of<br>proposed<br>solutions|Percent&nbsp;of<br>proposed<br>solutions| Number&nbsp;of<br/>correctly<br>resolved<br>solutions | Percent&nbsp;of<br>correctly<br>resolved<br>solutions | Score&nbsp;on<br>SWE&nbsp;Bench<br>Lite |
|:--------:|------------|---------:|---------:|----:|---:|--:|
| 1 | Aider with GPT-4o    | 419 | 73.5% | 87 | 81.3% | 15.3% |
| 2 | Aider with Opus      | 151 | 26.5% | 20 | 18.7% |  3.5% |
| **Total** | | **570** | **100%** | **107** | **100%** | **18.8%** |

If we break down the solutions solely by model,
we can see that aider with GPT-4o outperforms Opus.
This isn't a fair and direct comparison, because GPT-4o always took the first
turn and therefore got first crack at all the "easiest" problems.
Aider with Opus only ever saw problems that GPT-4o failed to
find proposed solutions for on its first try.

Aider with GPT-4o was producing higher quality proposed solutions,
with a greater chance of going on to be accepted as resolving the issue.
Again, this is biased by the turn ordering.
But other anecdotal evidence from earlier runs of the benchmark
also supports the observation that aider with GPT-4o is significantly stronger than Opus
for this benchmark.


| Agent      | Number&nbsp;of<br>proposed<br>solutions | Number&nbsp;of<br>correctly<br>resolved<br>solutions | Percent&nbsp;of<br>proposed<br>which<br>correctly<br>resolved<br>| 
|------------|---------:|---------:|---:|
| Aider with GPT-4o    | 419 | 87 |20.8% |
| Aider with Opus      | 151 | 20 |13.2% |
| **Total** | **570** | **107** |**18.8%** |


## Computing the benchmark score

After benchmarking,
a separate evaluation script was used to
test each of these solutions with the full test suite,
including the held out acceptance tests.
For this final acceptance testing, any edits that aider made to tests
were discarded.
This ensured that the correct,
unmodified test suite is used for acceptance testing.
The evaluation script compared the test results
with results from testing
the "gold" patch that was developed by a human to correctly solve the issue.
If they matched, the candidate solution correctly resolved the issue.

These acceptance tests were only ever run outside of aider
and the benchmark harness, and only to compute the number of
correctly resolved instances.
They were never run, used, or even visible during aider's attempts to solve the problems.

Aider correctly resolved 107 out of 570 SWE Bench instances that were benchmarked,
or 18.8%.

## Acknowledgments

Much thanks to the team behind the
[SWE Bench](https://www.swebench.com)
family of AI coding benchmarks.
Also thanks to Albert Örwall who has
[dockerized the SWE Bench evaluation scripts](https://github.com/aorwall/SWE-bench-docker)
making it faster, easier, and more reliable to run the acceptance tests.


## References

Below are the references for the SWE-Bench results
displayed in the graph at the beginning of this article.

- [13.9% Devin (benchmarked on 570 instances)](https://www.cognition.ai/post/swe-bench-technical-report)
- [13.8% Amazon Q Developer Agent (benchmarked on 2294 instances)](https://www.swebench.com)
- [12.5% SWE- Agent + GPT-4 (benchmarked on 2294 instances)](https://www.swebench.com)
- [10.6% AutoCode Rover (benchmarked on 2294 instances)](https://arxiv.org/pdf/2404.05427v2)
- [10.5% SWE- Agent + Opus (benchmarked on 2294 instances)](https://www.swebench.com)

The graph contains average pass@1 results for AutoCodeRover.
The [AutoCodeRover GitHub page](https://github.com/nus-apr/auto-code-rover)
features their pass@3 results
without being clearly labeled.
Table 2 of their
[paper](https://arxiv.org/pdf/2404.05427v2)
reports an `ACR-avg` result of 10.59% which is an average pass@1 result.

The [official SWE Bench Lite leaderboard](https://www.swebench.com)
only accepts pass@1 results.


