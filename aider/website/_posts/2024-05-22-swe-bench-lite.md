---
title: How aider scored SOTA 26.3% on SWE Bench Lite
excerpt: Aider achieved this result mainly through its existing features that focus on static code analysis, reliable LLM code editing, and pragmatic UX for AI pair programming.
highlight_image: /assets/swe_bench_lite.jpg
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# How aider scored SOTA 26.3% on SWE Bench Lite
 
[Aider scored 26.3%](https://github.com/swe-bench/experiments/pull/7)
on the
[SWE Bench Lite benchmark](https://www.swebench.com),
achieving a state-of-the-art result. 
The previous top leaderboard entry was 20.3%
from Amazon Q Developer Agent.

See also [aider's SOTA result on the main SWE Bench](https://aider.chat/2024/06/02/main-swe-bench.html).

[![SWE Bench Lite results](/assets/swe_bench_lite.svg)](https://aider.chat/assets/swe_bench_lite.svg)

**All of aider's results reported here are pass@1 results,
obtained without using the SWE Bench `hints_text`.**
All results in the above chart are unhinted pass@1 results.
Please see the [references](#references)
for details on the data presented in this chart.
It was corrected on 5/30/24 to reflect apples-to-apples comparisons,
using pass@1 results from AutoCodeRover
and results from OpenDevin that don't use hints.
The [official SWE Bench Lite leaderboard](https://www.swebench.com)
only accepts pass@1 results that do not use hints.

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
aider was launched in each problem's git repository
with the problem statement
submitted as the opening chat message from "the user."
After that aider runs as normal, with the following modifications:

- Aider's suggestions were always accepted without user approval.
- A simple harness was used to retry the SWE Bench problem if aider produced code that wasn't *plausibly correct*.
Plausibly correct means that aider reported that it had successfully edited the repo
without causing syntax errors or breaking any *pre-existing* tests.
- If the solution isn't plausible, the harness launches aider to try again from scratch,
alternating between using aider with GPT-4o and Opus.
- If no plausible solution is found after six tries, the harness picks the solution
with the fewest edit/lint/test problems.

It's important to be clear that
*aider and the benchmark harness
only had access to the pre-existing tests in each problem's repo*.
The held out "acceptance tests" were *only* used
after benchmarking to compute statistics on which problems aider
correctly resolved.

The [full harness to run aider on SWE Bench Lite is available on GitHub](https://github.com/Aider-AI/aider-swe-bench).

The benchmarking process was similar to how a developer might use aider to
resolve a GitHub issue:

- They could launch aider in their repo with the command below, which
tells aider they want to accept every suggestion
and to use pytest to run tests.
  - `aider --yes --test-cmd pytest`
- They could start the chat by pasting in the URL or text of a GitHub issue.
Aider will pull in the URL's content and then try and solve the issue.
- If aider doesn't produce code that lints and tests clean, the user might decide to revert the changes and try again, maybe using aider with a different LLM this time.
[Aider is tightly integrated with git](https://aider.chat/docs/git.html),
so it's always easy to revert AI changes that don't pan out.

Outside a benchmark setting, it's probably
unwise or at least highly inefficient
to let *any* AI agent run unsupervised on your code base.
The reason aider is intended to be used interactively
is so that the user can participate and direct aider's work and approve suggestions.
This way the user can offer immediate feedback or corrections if their initial
instructions turn out to be ambiguous,
or if the AI starts going down a wrong path.

## Aider with GPT-4o alone was SOTA

Running the benchmark harness
only using aider with GPT-4o to find plausible solutions
achieved a score of 25.0%.
This was itself matching the state-of-the-art, before being surpassed by the main
result being reported here
that used aider with both GPT-4o & Opus.

As noted below, a single attempt using Aider with GPT-4o tied
the current top entry on the leaderboard.

## Aider with GPT-4o & Opus

The benchmark harness alternated between running aider with GPT-4o and Opus.
The harness proceeded in a fixed order, always starting with GPT-4o and
then alternating with Opus until a plausible solution was found for each
problem.

The table below breaks down the plausible solutions that
were found for the 300 problems.
It also provides details on the 79 that were ultimately
verified as correctly resolving their issue.
Some noteworthy observations:

- *Just the first attempt* of Aider with GPT-4o resolved 20.3% of the problems, which ties the Amazon Q Developer Agent currently atop the official leaderboard.
- Including the second attempt, Aider with GPT-4o and Opus scored 23.6% on the benchmark.
These first two attempts obtained ~75% of all plausible and ~90% of all resolved solutions.
- A long tail of solutions continued to be found using both models including one correctly resolved solution on the final, sixth attempt of that problem.


| Attempt | Agent |Number&nbsp;of<br>plausible<br>solutions|Percent&nbsp;of<br>plausible<br>solutions| Number&nbsp;of<br/>correctly<br>resolved<br>solutions | Percent&nbsp;of<br>correctly<br>resolved<br>solutions | Score&nbsp;on<br>SWE&nbsp;Bench<br>Lite |
|:--------:|------------|---------:|---------:|----:|---:|--:|
| 1 | Aider with GPT-4o    | 208 | 69.3% | 61 | 77.2% | 20.3% |
| 2 | Aider with Opus      |  49 | 16.3% | 10 | 12.7% |  3.3% |
| 3 | Aider with GPT-4o    |  20 |  6.7% |  3 |  3.8% |  1.0% |
| 4 | Aider with Opus      |   9 |  3.0% |  2 |  2.5% |  0.7% |
| 5 | Aider with GPT-4o    |  11 |  3.7% |  2 |  2.5% |  0.7% |
| 6 | Aider with Opus      |   3 |  1.0% |  1 |  1.3% |  0.3% |
| **Total** | | **300** | **100%** | **79** | **100%** | **26.3%** |


If we break down the solutions solely by model,
we can see that aider with GPT-4o outperforms Opus.
This isn't a fair and direct comparison, because GPT-4o always took the first
turn and therefore got first crack at all the "easiest" problems.
Aider with Opus only ever saw problems that GPT-4o failed to
find plausible solutions for on its first try.

Aider with GPT-4o was producing higher quality plausible solutions,
with a greater chance of going on to be accepted as resolving the issue.
Again, this is biased by the turn ordering.
But other anecdotal evidence from earlier runs of the benchmark
also supports the observation that aider with GPT-4o is significantly stronger than Opus
for this benchmark.


| Agent      | Number&nbsp;of<br>plausible<br>solutions | Number&nbsp;of<br>correctly<br>resolved<br>solutions | Percent&nbsp;of<br>plausible<br>which<br>correctly<br>resolved<br>| 
|------------|---------:|---------:|---:|
| Aider with GPT-4o    | 239 | 66 |27.6% |
| Aider with Opus      |  61 | 13 |21.3% |
| **Total** | **300** | **79** |**26.3%** |

## Repository map, not RAG

The crucial first step in solving a SWE Bench problem is figuring out
which parts of the repo are relevant and which files need to be edited.
Most coding agents use some combination of RAG, vector search
and providing the LLM with
tools to interactively explore the code base.

Aider instead uses a
[repository map](https://aider.chat/2023/10/22/repomap.html)
to help the LLM understand the 
layout, code structure, and content of a git repo.
The repo map is created through static analysis of the code's
abstract syntax tree and call graph
to provide a compact and powerful summary of the entire code base.
The map is constantly
tailored to show
repo context that is relevant to the current state of the chat conversation.
This is done by performing a graph optimization on the code's call graph.

When the user asks for a change to their code, the LLM can use the repo map
to decide which files to edit.
The LLM simply returns a normal text response explaining which files
it needs to edit and why.
Aider notices when the LLM mentions filenames from the repo,
and asks the user if they should be added to the chat.
Adding a file to the chat allows the LLM to see the full contents
of the file and edit it.

<div class="chat-transcript" markdown="1">

#### Please add a new /factorial/N endpoint.

To add a new /factorial/N endpoint, the most likely file that needs to be edited is app.py.
Please add app.py to the chat so I can proceed with the changes.

> app.py  
> Add these files to the chat? yes

</div>

This is a convenient and natural workflow for interactive chat,
and it worked well for the SWE Bench problems.
Aider successfully identified the correct file to edit
in 70.3% of the benchmark tasks.

We can determine which file needs to be edited using the "gold" patch
which is associated with each SWE Bench task.
This patch was created by a human developer
to solve the issue, and therefore reveals a file which can
be edited to solve the problem.
Of course aider is not able to see or use the gold patch
or the file names it contains in any way.
This information was only used to compute
statistics outside the benchmarking process.


## Reliable code editing

Once files have been selected for editing,
the next step is of course to edit the source code to fix the problem.

Aider goes to great lengths to ensure that LLMs can not just write code,
but reliably *edit* code.
Aider has a collection of prompting strategies and code editing backends which have
been honed through
[extensive benchmarking](https://aider.chat/docs/leaderboards/).
These foundational capabilities help ensure that aider can
properly integrate code from LLMs into an existing code base and source files.

The repository map helps here too, making sure that the LLM
can see relevant classes, functions and variables from the entire repo.
This helps ensure that the project's existing APIs and conventions are
respected and utilized when new code is added.

Regardless, there are still cases where aider may be unable to cleanly
complete the edits specified by the LLM.
This is usually because the LLM has failed to conform to the editing
instructions in its system prompt.
When aider completes, it returns an editing outcome that indicates
whether it was able to successfully apply all edits.
The benchmark harness uses this editing status as
one criteria to determine if aider has
created a plausible solution.

## Linting and fixing

Another key criteria for a plausible solution is that it passes basic
linting, which means that the code has no syntax
or other fatal errors.
[Aider lints code](https://aider.chat/2024/05/22/linting.html)
after every LLM edit and offers to automatically fix
any problems.

Aider ships with built-in linters based on tree-sitter
which work with most popular programming languages.
Aider shows linting errors to the LLM in a novel format,
using the abstract syntax tree to display relevant code context for each
error.
This context helps LLMs understand the problem and
make the correct changes to resolve it.

<div class="chat-transcript" markdown="1">

```
app.py:23:36: F821 undefined name 'num'  
  
app.py:  
...⋮...  
  6│class LongNum:  
...⋮...  
 19│    def expound(self, threshold):  
 20│        number = self.basis  
 21│        while number < threshold:  
 22│            number *= self.factor  
 23█        return num  
 24│  
 25│  
...⋮...  
```  

> Attempt to fix lint errors? yes

</div>

In the benchmark, these linting suggestions are always accepted.
At completion,
aider reports a linting outcome that
indicates if it was able to produce
code without any outstanding linting errors.
The benchmark harness uses this status as
one of the criteria to determine if aider has
created a plausible solution.

## Testing and fixing

The final crtieria for a plausible solution is that 
all tests must be passing.
Aider can be configured with the command to run tests for a repo,
and will automatically attempt to fix any test failures.

A user working on a python project might configure testing
by launching aider like this:

```
aider --test-cmd pytest
``` 

For the benchmark, aider is configured with a test command that will run the
tests that already exist in each problem's repository.
SWE Bench problems are based on repositories from large open
source projects with extensive existing test suites.
This means that
testing will fail if aider has broken any of these
pre-existing tests or if any new
tests that it created aren't passing.

As with editing and linting, aider reports a testing outcome
that indicates if it completed with any outstanding failing tests.
The benchmark harness uses this status when deciding if aider
has produced a plausible solution.

To be clear, *aider cannot run or even see the held out "acceptance tests"* that
are used to judge if a proposed solution correctly
resolves the problem.
Those tests are only run outside of aider and the benchmark harness,
to compute the final benchmark statistics.

## Finding a plausible solution

Each time aider executes, it reports
the outcome of the editing, linting, and testing
steps.
Each of these steps may complete successfully or
return a status that indicates that there were outstanding
problems that remain unresolved.

The benchmark harness uses these outcomes to determine if
aider has produced a plausible
solution to the current SWE Bench task.
A plausible solution is one where aider
returns saying that it 
edited the repo with no outstanding
edit, lint, or test errors.
In this case, aider's changes are recorded
as the SWE Bench `model_patch` to be evaluated later with the
acceptance tests.

If the solution is not plausible, another
instance of aider is launched again from scratch on the same problem.
The harness alternates launching aider with GPT-4o and Opus to solve the problem,
and gives each model three attempts -- for a total of six attempts.
As soon as a plausible solution is found, it is accepted and the
harness moves on to the next SWE Bench instance.

It's worth noting that repositories may have lint or test errors
present before aider even starts to edit them.
Whether unresolved errors were caused by aider or were pre-existing,
there will be instances where
no plausible solution is
found after six tries.

If all six attempts fail to produce a plausible solution,
then the "best" solution available is selected as the
`model_patch`.
Which of the non-plausible solutions to use is determined
by ignoring the testing outcome
and prioritizing solutions in the following order:

 - Pick a solution where editing and linting were completed successfully.
 - Pick a solution where editing was at least partially successful and linting succeeded.
 - Pick a solution where editing was successful.
 - Pick a solution where editing was at least partially successful.

## Computing the benchmark score

The benchmark harness produced a plausible solution for each of the 300
SWE Bench Lite instances and saved it as the `model_patch`.

A separate evaluation script was used to
test each of these solutions with the full test suite,
including the held out acceptance tests.
For this final acceptance testing, any edits that aider made to tests
are discarded.
This ensures that the correct,
unmodified test suite is used for acceptance testing.
The evaluation script compares the test results
with results from testing
the "gold" patch that was developed by a human to correctly solve the issue.
If they match, the candidate solution has correctly resolved the issue.

These acceptance tests are only ever run outside of aider
and the benchmark harness, and only to compute the number of
correctly resolved instances.
They are never run, used, or even visible during aider's attempts to solve the problems.

Aider correctly resolved 79 out of 300 SWE Bench Lite instances, or 26.3%.

## Acknowledgments

Much thanks to the team behind the
[SWE Bench](https://www.swebench.com)
family of AI coding benchmarks.
Also thanks to Albert Örwall who has
[dockerized the SWE Bench evaluation scripts](https://github.com/aorwall/SWE-bench-docker)
making it faster, easier, and more reliable to run the acceptance tests.


## References

All of aider's results reported here are pass@1 results,
obtained without using the SWE Bench `hints_text`.

The "aider agent" internally makes multiple "attempts" at solving the problem,
but it picks and returns one single candidate solution.
Only that one candidate solution is evaluated with the acceptance tests
and contributes to the benchmark score.
Thus it is a pass@1 result.

This is contrast to a pass@N result for N>1, where N attempts are made
and all N solutions are evaluated by the acceptance tests.
If *any* of the N solution pass, that counts as a pass@N success.

Below are the references for the other pass@1 unhinted SWE-Bench results
displayed in the graph at the beginning of this article.

- [20.3% Amazon Q Developer Agent (v20240430-dev)](https://www.swebench.com)
- [19.0% AutoCodeRover](https://www.swebench.com/)
- [18.0% SWE-Agent + GPT-4](https://www.swebench.com)
- [16.7% OpenDevin](https://github.com/OpenDevin/OpenDevin/issues/2149)
- [11.7% SWE-Agent + Opus](https://www.swebench.com)

Note, the graph was corrected on 5/30/24 as follows.

The graph now contains AutoCodeRover's average pass@1 results.
Previously it displayed pass@3 results, which are
not comparable
to the pass@1 results for aider being reported here.
The [AutoCodeRover GitHub page](https://github.com/nus-apr/auto-code-rover)
features pass@3 results
without being clearly labeled.

The graph now contains the best OpenDevin results obtained without using
the SWE Bench `hints_text` to provide hints to the agent.
The previous graph contained their hinted result,
which is not comparable
to the unhinted aider results being reported here.
[OpenDevin reported hinted results](https://x.com/gneubig/status/1791498953709752405)
without noting that hints were used.
