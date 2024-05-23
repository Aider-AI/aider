---
title: Aider scores 26.3% on SWE Bench Lite
excerpt: Aider scored 26.3% on SWE Bench Lite, achieving a state of the art result.
highlight_image: /assets/swe_bench_lite.jpg
draft: true
---

# Aider scores 26.3% on SWE Bench Lite
 
Aider scored 26.3%
on the
[SWE Bench Lite benchmark](https://www.swebench.com),
achieving a state-of-the-art result. 
The current top leaderboard entry is 20.3%
from Amazon Q Developer Agent.
The best result reported elsewhere online seems to be
[22.3% from AutoCodeRover](https://github.com/nus-apr/auto-code-rover).

[![SWE Bench Lite results](/assets/swe_bench_lite.svg)](https://aider.chat/assets/swe_bench_lite.svg)

## Interactive, not agentic

Aider achieved this result mainly through its focus on static code analysis,
reliable LLM code editing,
and pragmatic workflows for interactive pair programming with AI.
Aider intentionally has quite limited and narrow "agentic behavior":
it doesn't require a highly detailed upfront "spec" from the user,
use RAG or vector search, farm out sub-problems to an army of LLMs,
allow the LLM to use tools,
or perform web searches,
etc.

Aider is first and foremost a tool for engineers to get real work done in
real code bases through a pair programming chat style interface.
When a user asks aider for a change, they see the edits performed in real-time,
and aider may also then offer additional
help like fixing lint or test errors.
In normal use, the user is in full interactive control. 
This lets them quickly steer misunderstandings back on course and
avoid wasted time, code reviews and token costs.


## Benchmark methodology

For the benchmark, 
aider was launched in each problem's git repository
with the problem statement
submitted as the opening chat message from "the user."
After that aider runs as normal, with the following modifications:

- Aider's suggestions were always accepted without user approval.
- A simple harness was used to retry the SWE Bench problem if aider produced code that wasn't *plausibly correct*.
Plausibly correct means that aider concluded that it had successfully edited the repo
without causing syntax errors or breaking any *pre-existing* tests.
- If the solution isn't plausible, the harness launches aider to try again from scratch,
alternating between using aider with GPT-4o and Opus.
- If no plausible solution is found after six tries, the harness picks the solution
with the least amount of edit/lint/test problems.

It's important to be clear that during benchmarking
*aider only had access to the pre-existing tests in the repo*.
It could not see or run the held out "acceptance tests" that are used later to see if the
SWE Bench problem was correctly resolved.

The benchmarking process was similar to how a developer might use aider to
resolve a GitHub issue:

- They could launch aider in their repo with the command below, which
tells aider they want to accept every suggestion
and to use pytest to run tests.
  - `aider --yes --test-cmd pytest`
- Paste the URL or text of a GitHub issue into the chat. Aider will pull in the URL's content and then try and solve the issue.
- If aider doesn't produce code that lints and tests clean, the user might decide to revert the changes and try again, maybe using aider with a different LLM this time.
[Aider is tightly integrated with git](https://aider.chat/docs/faq.html#how-does-aider-use-git),
so it's always easy to revert AI changes that don't pan out.

Outside a benchmark setting, it's probably
unwise to let *any* AI agent run unsupervised on your code base.
Aider is intended to be used as an interactive pair-programming chat,
where the user participates to direct aider's work and approve suggestions.
This way the user can offer immediate feedback or corrections if their initial
instructions turn out to be ambiguous,
or if the AI starts going down a wrong path.

## Aider with GPT-4o alone was SOTA

Running the SWE Bench Lite benchmark using aider with just GPT-4o
achieved a score of 25%.
This was itself a state-of-the-art result, before being surpassed by the main
result being reported here
that used aider with both GPT-4o & Opus.

## Aider with GPT-4o & Opus

The benchmark harness alternated between running aider with GPT-4o and Opus.
The harness proceeded in a fixed order, always starting with GPT-4o and
then alternating with Opus until a plausible solution was found.

The table below breaks down the 79 solutions that were ultimately
verified as correctly resolving their issue.
Some noteworthy observations:

- Aider with GPT-4o on the first attempt immediately found 69% of all plausible solutions which accounted for 77% of the correctly resulted problems.
- ~75% of all plausible and ~90% of all resolved solutions were found after one attempt from aider with GPT-4o and Opus.
- A long tail of solutions continued to be found by both models including one resolved solution on the final, sixth attempt of that problem.


| Attempt | Agent |Number<br>plausible<br>solutions|Percent of<br>plausible<br>solutions| Number<br/>correctly<br>resolved | Percent<br>of correctly<br>resolved |
|:--------:|------------|---------:|---------:|----:|---:|
| 1 | Aider with GPT-4o    | 208 | 69.3% | 61 | 77.2% |
| 2 | Aider with Opus      |  49 | 16.3% | 10 | 12.7% |
| 3 | Aider with GPT-4o    |  20 |  6.7% |  3 |  3.8% |
| 4 | Aider with Opus      |   9 |  3.0% |  2 |  2.5% |
| 5 | Aider with GPT-4o    |  11 |  3.7% |  2 |  2.5% |
| 6 | Aider with Opus      |   3 |  1.0% |  1 |  1.3% |
| **Total** | | **300** | **100%** | **79** | **100%** |

If we break down correct solutions purely by model,
we can see that aider with GPT-4o outperforms Opus.
This isn't a fair and direct comparison, because GPT-4o always took the first
turn at solving and therefore got to solve all the "easiest" problems.
Aider with Opus only ever saw the problems that GPT-4o failed to solve on the first attempt.

Aider with GPT-4o was producing higher quality plausible solutions,
with a greater chance of going on to be accepted as resolving the issue.
Other anecdotal evidence from earlier runs of the benchmark
also supports the observation that aider with GPT-4o is significantly stronger than Opus
for this endeavor.


| Agent      | Number<br>plausible<br>solutions | Number<br>correctly<br>resolved | Percent<br>plausible<br>which<br>resolved| 
|------------|---------:|---------:|---:|
| Aider with GPT-4o    | 239 | 66 |27.6% |
| Aider with Opus      |  61 | 13 |21.3% |
| **Total** | **300** | **79** |**26.3%** |

## Repository map, not RAG

The crucial first step in solving a SWE Bench problem is figuring out
which parts of the repo are relevant and which files need to be edited.
Most coding agents use some combination of RAG, vector search
and arming the LLM with
tools to interactively explore the code base.

Aider instead uses a
[repository map](https://aider.chat/2023/10/22/repomap.html)
to help the LLM understand the 
layout, code structure, and content of a git repo.
The repo map is created from the code's AST and call graph
to provide a compact and powerful summary of the entire code base.
The map is constantly
tailored to show
repo context that is relevant to the current state of the chat conversation.
This is done by performing a graph optimization on the code's call graph.

When the user asks for a change to their code, the LLM uses the repo map
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
and it worked well for the SWE Bench tasks.
Aider successfully identified the correct file to edit
in 70.3% of the benchmark tasks.

We can determine which file needed to be edited using the "gold" patch
which is associated with SWE Bench Task.
This patch was created by a human developer
to solve the issue, and therefore reveals a file which can
be edited to solve the problem.
Of course aider is not able to see or use the gold patch
or the file names it contains in any way.
This information was only used to compute
statistics after the benchmarking was completed. 


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
respected when new code is added.

Regardless, there are still cases where aider may be unable to cleanly
complete the edits specified by the LLM.
This is usually because the LLM has failed to conform to the editing
instructions in its system prompt.
When aider completes, it returns an editing outcome that indicates
whether it was able to successfully complete all edits.
The benchmark harness used this editing status as
one criteria to determine if aider has
created a plausible soultion.

## Linting and fixing

One key criteria for a plausible solution is that it passes basic
linting, which means that the code is valid and without syntax
or other fatal errors.
[Aider lints code](https://aider.chat/2024/05/22/linting.html)
after every LLM edit and offers to automatically fix
any problems.

Aider shows linting errors to the LLM in a novel format,
using the abstract syntax tree (AST) to display relevant code context for each
error.
This context increases the ability of the LLM to understand the problem and
make the correct changes to resolve it.

<div class="chat-transcript" markdown="1">

```
app.py:23:36: F821 undefined name 'num'  
app.py:41:16: F541 f-string is missing placeholders  
  
app.py:  
...⋮...  
  6│class LongNum:  
  7│    def __init__(self, num):  
  8│        """  
  9│        Initialize the number.  
 10│        """  
...⋮...  
 19│    def __str__(self):  
 20│        """  
 21│        Render the number as a string.  
 22│        """  
 23█        return str(num)  
 24│  
 25│  
 26│@app.route('/subtract/<int:x>/<int:y>')  
...⋮...  
 38│@app.route('/divide/<int:x>/<int:y>')  
 39│def divide(x, y):  
 40│    if y == 0:  
 41█        return f"Error: Cannot divide by zero"  
 42│    else:  
 43│        result = x / y  
 44│        return str(result)  
 45│  
...⋮...  
```  

> Attempt to fix lint errors? yes

</div>

In the benchmark, these linting suggestions are always accepted.
At completion,
aider reports a linting outcome that
indicates if it was able to ultimately produce
code without any outstanding linting errors.
The benchmark harness used this status as
one of the criteria to determine if aider has
created a plausible soultion.

## Testing and fixing

Another key crtieria for a plausible solution is that it must
not have any broken tests.
Aider can be configured with the command needed to run tests for a repo,
and can automatically attempt to fix any testing errors.

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

As with editig and linting, aider reports a testing outcome
that indicates if it completed with any outstanding testing errors.
The benchmark harness uses this status when deciding if aider
has produced a plausible solution.

To be clear, *aider cannot run or even see the "acceptance tests"*
that are used to determine if a proposed solution correctly
resolves the problem.
Those tests are only run outside of aider and the benchmark harness,
to compute the final benchmark score.

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
Whether errors are caused by aider or were pre-existing,
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

The benchmark harness produces one candidate solution for each of the 300
SWE Bench Lite instances and saves it as a `model_patch`.
A separate evaluation script 
tests each of these results with the acceptance tests.
It verifies that they pass as expected from a correct solution, like
the "gold" patch developed by a human to solve the issue.

These `test_patch` acceptance tests are only ever run outside of aider
and the benchmark harness, and only to compute the number of
correctly resolved instances.
They are never run, used, or even visible during the attempts to solve the problems.

Aider correctly resolved 79 out of 300 SWE Bench Lite instances, or 26.3%.

## Acknowledgments

Much thanks to the team behind the
[SWE Bench](https://www.swebench.com)
family of AI coding benchmarks.
Also thanks to Albert Örwall who has
[dockerized the SWE Bench evaluation scripts](SWE-bench-docker)
making it faster, easier, and more reliable to run the acceptance tests.


