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
The best result reported elsewhere seems to be
[13.9% from Devin](https://www.cognition.ai/post/swe-bench-technical-report).

This result on the main SWE Bench is in addition to
[aider's SOTA result on the easier SWE Bench Lite](https://aider.chat/2024/05/22/swe-bench-lite.html)
that was reported recently.

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

Benchmarking was conducted as follows:

- Aider with GPT-4o was launched in each problem's git repository
with the problem statement
submitted as the opening chat message from "the user".
- After that aider ran as normal, except all of aider's
suggestions were always accepted without user approval.
- A [simple harness](https://github.com/paul-gauthier/aider-swe-bench#the-aider-agent) was used to retry the SWE Bench problem if aider produced code that wasn't *plausibly correct*.
Plausibly correct means that aider reported that it had successfully edited the repo
without causing syntax errors or breaking any *pre-existing* tests.
- If the solution from aider with GPT-4o wasn't plausible, the harness launched aider to try again from scratch, this time using Claude 3 Opus.
- If no plausible solution is found after those two tries, the harness picks the "most plausible" solution with the fewest edit/lint/test problems.

It's important to be clear that
*aider and the benchmark harness
only had access to the pre-existing tests in each problem's repo*.
The held out "acceptance tests" were *only* used
after benchmarking to compute statistics on which problems aider
correctly resolved.

This is the same methodology
that was used for [aider's recent SOTA result on SWE Bench Lite](https://aider.chat/2024/05/22/swe-bench-lite.html).
Aider alternated between GPT-4o and Opus for up to 6 total attempts
on the Lite benchmark.
Due to the increased token costs involved in running
the main SWE Bench benchmark, aider was limited to 2 total attempts.
Problems from the main SWE Bench dataset
are more difficult and involve edits to
more than one source file,
which increased the token costs of solving each problem.
Further, aider was benchmarked on 570 SWE Bench problems
versus only 300 Lite problems,
adding another factor of ~two to the costs.

For a detailed discussion of the methodology, please see the
[article about aider's SWE Bench Lite results](https://aider.chat/2024/05/22/swe-bench-lite.html).
The [aider SWE Bench repository on GitHub](https://github.com/paul-gauthier/aider-swe-bench) also contains
the harness and analysis code used for the benchmarks.

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

Using aider with GPT-4o to make a single attempt at solving each problem
achieved a score of 17.0%.
This was itself a state-of-the-art result, before being surpassed by the main
result being reported here
that used aider with both GPT-4o & Opus.

## Aider with GPT-4o & Opus

The benchmark harness ran aider with GPT-4o to try
and solve the problem. If
no plausible solution was found, it ran aider with Opus
to try and solve the problem.

The table below breaks down the proposed solutions that
were found from each attempt for the 570 problems.
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

## Non-plausible but correct solutions?

A solution doesn't have to be plausible in order to correctly resolve the issue.
Recall that plausible is simply defined as aider
reporting that it successfully edited files,
repaired and resolved any linting errors
and repaired tests so that they all passed.
But there are lots of reasons why aider might fail to do those things
and yet the solution is still a correct solution that will pass
acceptance testing:

- There could be pre-existing failing tests in the repo,
before aider even starts working on the SWE Bench problem.
Aider may not resolve such issues, and yet they may turn out not to be
relevant to the acceptance testing.
The SWE Bench acceptance testing just confirms that tests pass or fail
in the same pattern as the "gold patch" developed by a human to solve the
problem.
Some tests may still fail, and that's ok as long they fail for the gold
patch too.
- There could be pre-existing linting problems in the repo,
which are in code paths that are irrelevant to the problem being solved
and to acceptance testing.
If aider is unable to resolve them, the solution may still be valid
and pass acceptance testing.
- Aider may report editing errors because it doesn't think it was
able to successfully apply all the edits the LLM specified.
In this scenario, the LLM has specified edits in an invalid
format that doesn't comply with its
system prompt instructions.
So it may be that the LLM was asking for redundant or otherwise
irrelevant edits, such that outstanding edit errors are actually not fatal.

This is why the first row in the table above
shows GPT-4o accounting for 15.3% of the benchmark score,
which is different than the 17.0% result reported earlier
for aider with just GPT-4o.
The second attempt from Opus may propose solutions which
are "more plausible" than some of GPT-4's non-plausible solutions,
but which are actually incorrect solutions.
These more plausible but incorrect solutions can
eclipse the earlier non-plausible correct
solution.
Luckily the full set of later attempts usually provide a net increase in the overall
number of resolved solutions, as is the case here.

The table below breaks down the plausibility of each solution proposed by
aider with GPT-4o and with Opus, and indicates which were actually
correct solutions.

|Row|Aider<br>w/GPT-4o<br>solution<br>plausible?|Aider<br>w/GPT-4o<br>solution<br>resolved<br>issue?|Aider<br>w/Opus<br>solution<br>plausible?|Aider<br>w/Opus<br>solution<br>resolved<br>issue?|Count|
|---:|--:|--:|--:|--:|--:|
|  1 | plausible       | resolved        | n/a             | n/a             |  73 |
|  2 | plausible       | not resolved    | n/a             | n/a             | 181 |
|  3 | non-plausible   | resolved        | plausible       | resolved        |   1 |
|  4 | non-plausible   | resolved        | plausible       | not resolved    |   2 |
|  5 | non-plausible   | resolved        | non-plausible   | resolved        |  16 |
|  6 | non-plausible   | resolved        | non-plausible   | not resolved    |   5 |
|  7 | non-plausible   | not resolved    | plausible       | resolved        |  12 |
|  8 | non-plausible   | not resolved    | plausible       | not resolved    |  53 |
|  9 | non-plausible   | not resolved    | non-plausible   | resolved        |   4 |
| 10 | non-plausible   | not resolved    | non-plausible   | not resolved    | 216 |
| 11 | non-plausible   | not resolved    | n/a             | n/a             |   7 |

Rows 1-2 show the case where the first solution found
by aider with GPT-4o was plausible. Of those, 73 went on to be deemed as resolving the issue,
while 181 were not in fact correct solutions. Opus never got a try
at solving these problems, because the harness stopped once a
plausible solution was found.

The remaining rows consider cases where aider with GPT-4o
did not find a plausible solution, so Opus got a turn to try and solve.
Rows 3-6 are cases where GPT-4o's non-plausible solutions were
actually found to be correct in hindsight,
but in row 4 we can see that aider with Opus overrides
2 of them with a plausible-but-incorrect
solution.

In rows 5-6 & 9-10 we can see that both GPT-4o and Opus
produced non-plausible solutions,
and which one was selected has to do with the
[details about which solution the harness considered "most plausible"]().

Row 11 contains cases where Opus returned errors due to context window
exhaustion or other problems. 
In these cases aider with Opus was unable to produce any solutions.

## Computing the benchmark score

Benchmarking produced one candidate solution for each of
the 570 SWE Bench problems.

A separate evaluation script was used to
test each of these solutions with the full test suite,
including the held out acceptance tests.
For this final acceptance testing, any edits that aider made to tests
were discarded.
This ensured that the correct,
unmodified test suite was used for acceptance testing.
The evaluation script compared each candidate solution's test results
with results from testing
the "gold" patch that was developed by a human to correctly solve the issue.
If they matched, the candidate solution correctly resolved the issue.

These acceptance tests were only ever run outside of aider
and the benchmark harness, and only to compute statistics about the
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


