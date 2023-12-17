
# Fixing GPT-4 Turbo laziness with unified diffs

![robot flowchart](../assets/udiff.jpg)


Aider now asks GPT-4 Turbo to use [unified diffs](https://www.gnu.org/software/diffutils/manual/html_node/Unified-Format.html) to edit your code when you request new features, improvements, bug fixes, test cases, etc.
This new support for unified diffs massively reduces GPT-4 Turbo's habit of being a "lazy" coder.

There are abundant anecdotes
about GPT-4 Turbo writing half completed code filled with comments that give
homework assignments to the user
like "...omitted for brevity..." or "...add logic here...".
Aider's new unified diff edit format significantly reduces this sort of lazy coding,
producing much better quantitative scores on a new "laziness benchmark".

Before trying to reduce laziness, I needed a way to quantify and measure
the problem.
I developed a new
benchmarking suite designed to both provoke and quantify lazy coding.
It consists of 39 python refactoring tasks,
which ask GPT to remove a non-trivial method from a class and make it
a stand alone function.

GPT-4 Turbo is prone to being lazy on this sort of task, because it's mostly a
"cut & paste" of code from one place in a file to another.
GPT often creates the new function with a body that is empty except for
a comment like
"...include the body of the original method..."

This new laziness benchmark produced the following results with `gpt-4-1106-preview`:

- **GPT-4 Turbo only scored 15% as a baseline** using aider's existing "SEARCH/REPLACE block" edit format. This confirms the anecdotes that GPT-4 Turbo is quite lazy when coding, and serves as a baseline for comparison.
- **Aider's new unified diff edit format raised the score to 65%**.
- **A system prompt based on widely circulated folklore only scored 15%, same as the baseline.** This experiment used the existing "SEARCH/REPLACE block" format with an additional prompt that claims the user is blind, has no hands, will tip $2000 and has suffered from "truncated code trauma".

The older `gpt-4-0613` also did better on the laziness benchmark by using unified diffs.
The benchmark was designed to work with large source code files, many of
which exceeded GPT-4's 8k context window.
This meant that 28% of tasks exhausted the context window and were marked as a fail,
significantly dragging down GPT-4's performance on the benchmark.

- **GPT-4's baseline was 26%** using aider's existing "SEARCH/REPLACE block" edit format.
- **Aider's new unified diff edit format raised GPT-4's score to 59%**. 

Before settling on unified diffs,
I explored many other approaches to stop GPT-4 Turbo from eliding code
and replacing it with comments.
These efforts included prompts about being tireless and diligent,
use of OpenAI's function/tool calling capabilities and numerous variations on
aider's existing editing formats and other diff-like formats.
All in all, the results shared here reflect
an extensive investigation of possible solutions and
a large number of benchmarking runs of numerous varied approaches against
GPT-4 Turbo.

The result is aider's new support for a unified diff like
editing format which outperforms other potential solutions by a wide margin.
The rest of this article will describe aider's new refactoring benchmark
and the new unified diff editing format.
We will discuss some key design decisions involved in this new format,
and evaluate their significance using ablation experiments.


## Refactoring benchmark

Aider has long used a
[benchmark suite based on 133 Exercism python exercises]().
But these are mostly small coding problems,
usually requiring only a few dozen lines of code to solve.
GPT-4 Turbo was typically only lazy on 2-3 of these exercises:
the ones with the largest amount of code and which involved refactoring.
Rather than fully completing the refactor, GPT would often
just add a comment
referencing old code like
"...copy $USD formatting code here...".

Based on this observation, I set out to build a benchmark based on refactoring
a non-trivial amount of code from within fairly large source files.
To do this, I used python's `ast` module to analyze the
[Django repository]().

The goal was to search the Django repository to:

- Find source files that contain class methods which are non-trivial, having more than 100 AST nodes in their implementation.
- Focus on methods that are a smaller piece of a larger class, so they don't represent the bulk of the code in their class or the file. We want to find methods which are less than half the AST nodes present in their containing class.
- Find methods that do not make any use of their `self` parameter. This means they can be trivially refactored out of the class and turned into a stand-alone top-level function.

We can then turn each of these source files into a task for the benchmark,
using instructions like:

> Refactor the `_set_csrf_cookie` method in the `CsrfViewMiddleware` class to be a stand alone, top level function.
> Name the new function `_set_csrf_cookie`, exactly the same name as the existing method.
> Update any existing `self._set_csrf_cookie` calls to work with the new `_set_csrf_cookie` function.

A [simple python AST scanning script]() found 39 of these source files in the Django repository
and packaged them up as benchmark tasks using
the same format as Exercism exercises.

The tool also created a unit test for each task
which again uses the `ast` module to check that the refactor
was performed roughly correctly:

- The updated source file must parse as correct python, without `SyntaxError` or `IndentationError` exceptions. This is a powerful check that will surface any mechanical errors made when attempting to edit the source code.
- The target method must now exist as a top-level function in the file.
- This new top-level function must contain approximately the same number of AST nodes as the original class method. This ensures that GPT didn't elide code and replace it with comments.
- The original class must still be present in the file, and it must be smaller by about the number of AST nodes of the method which was removed. This helps confirm that the method was removed from the class, without other significant modifications.

To be clear, this is not a rigorous test that the refactor was performed correctly.
But it does serve as a basic sanity check that the refactor was essentially done as a cut & paste, without eliding any code as comments.
And it correlates well with other laziness metrics
gathered during benchmarking like the
introduction of new comments that contain "...".

The result is a pragmatic benchmark suite that provokes, detects and quantifies laziness.


## Unified diff editing format

The design and implementation of aider's new unified diff editing format
helped clarify some general principles, which I think are applicable to any effective
GPT-4 code editing format:

- FAMILIAR - Choose an edit format that GPT is already familiar with.
- SIMPLE - Choose a simple format that avoid escaping, syntactic overhead and brittle specifiers like line numbers or line counts.
- HIGH LEVEL - Encourage GPT to structure edits as new versions of substantive code blocks (functions, methods, etc), not as a series of surgical/minimal changes to individual lines of code.
- FLEXIBLE - Strive to be maximally flexible when interpreting GPT's edit instructions.

A helpful shortcut here is to have empathy for GPT, and imagine you are on
the other end of the conversation being tasked with specifying code edits.
Would you want to hand type a properly escaped json data structure
to specify surgical insert, delete, replace operations on specific code line numbers?
Would you want a typo, off-by-one line number or flubbed escape character to trigger an error
and force you to start over?

GPT is quantitatively better at code editing when you reduce the
burden of formatting edits by using a familiar, simple, high level
and flexible editing format.

### Choose a familiar editing format

Unified diffs are perhaps the most commonly used format for showing
how source code files have been changed.
This is because it is the default output format of `git diff`:

```diff
$ git diff hello.py
...
--- a/hello.py
+++ b/hello.py
@@ -1,5 +1,5 @@
 def main(args):
     # show a greeting

-    print("Hello!")
+    print("Goodbye!")
     return
```

Choosing such a familiar, popular output format means that GPT has
seen *many* examples in its training data.
GPT has therefore been extensively trained to generate
text that conforms to the unified diff syntax.
We won't need to provide many details and examples
in the system prompt, as it knows this format by name.

Unified diffs are
usually intended to be consumed by the
[patch](https://www.gnu.org/software/diffutils/manual/html_node/Merging-with-patch.html)
program.
They need to *accurately* reflect the original and updated file contents,
otherwise the patch command will fail to apply the changes.
Having GPT specify changes in a well-known format that is usually consumed by a
fairly rigid program like patch
seems to discourage it from
leaving informal editing instructions in comments
and being lazy
about writing all the needed code.

With unified diffs, GPT acts more like it's writing textual data intended to be read by a program,
not talking to a person.


### Use a simple editing format

Aider's [previous benchmark results](https://aider.chat/docs/benchmarks.html) made
it clear that simple editing formats
work much better than complex ones.
Even though OpenAI provides extensive support for
structured formats like json and function calls,
GPT is worse at editing code if you use them.
I repeated these and many other similar benchmarks against GPT-4 Turbo,
and again reached these same conclusions.

Informally, this is probably because stuffing *source code* into JSON is complicated
and error prone.
It likely takes a lot of the model's attention to escape and wrap code
in JSON containers.
Wrapping the python code
`print("On Windows use \"C:\\\"")`
as valid json is pretty painful and error prone:
`"print(\\"On Windows use \\"C:\\\\\\"\\")"`
Due to escaping issues GPT's code is often syntactically incorrect when it's
unpacked from the JSON container or the JSON decode just fails entirely.

On the other hand, the core of the unified diff format is extremely simple.
You include a hunk of the file that needs to be changed,
with every line prefixed by ether a *space* ` `, a *plus* `+` or a *minus* `-`.
These markers indicate an unchanged line, a new line to add or an existing line to remove.
There is no escaping, and very little other structure needed
to create a unified diff.

A unified diff looks pretty much like the code it is modifying.

The one complicated piece is the line numbers found at the start
of each hunk that look something like this: `@@ -2,4 +3,5 @@`.
This example is from a
hunk that will change lines 2-4 in the original file
into what will become lines 3-5 in the updated file.

You've probably read a lot of unified diffs without ever
caring about these line numbers,
because the diffs are usually perfectly sensible without them.
This is good news, because we're going to discard these numbers.

GPT is terrible at working accurately with source code line numbers.
This is a general observation about any use of line
numbers in editing formats,
backed up by many quantitative benchmark
experiments.
Specifically regarding line numbers in unified diffs,
GPT is frequently off-by-one, or labels a hunk as
being line numbers 2-4 of the file but the hunk actually contains 6 lines, etc.
GPT-4 isn't even close to being able to consistently
produce valid
line number headers.
Doing so requires far too much attention to numerical details to ensure
correctness and self-consistency.

So aider tells GPT not to include line numbers.
Instead, aider just interprets each hunk from the unified diffs
as a search and replace operation:

This diff:

```diff
@@ ... @@
 def main(args):
     # show a greeting

-    print("Hello!")
+    print("Goodbye!")
     return
```

Means we want to search the original source file for all the
*space* ` ` and *minus* `-` lines from the hunk:

```python
def main(args):
    # show a greeting

    print("Hello!")
    return
```

And then replace them with all the *space* ` ` and *plus* `+` lines:

```python
def main(args):
    # show a greeting

    print("Goodbye!")
    return
```

Simple, right?

## Encourage high level edits

The example unified diffs we've seen so far have all been single line changes,
which makes them pretty easy to read and understand.
Consider this slightly more complex change, which renames the variable `n` to
`number`:

``` diff
@@ ... @@
-def factorial(n):
+def factorial(number):
     "compute factorial"

-    if n == 0:
+    if number == 0:
         return 1
     else:
-        return n * factorial(n-1)
+        return number * factorial(number-1)
```

The following "high level diff" of the same
change is not as succinct as the minimal diff above,
but it is much easier to see two different coherent versions of the
`factorial()` function.

``` diff
@@ ... @@
-def factorial(n):
-    "compute factorial"
-
-    if n == 0:
-        return 1
-    else:
-        return n * factorial(n-1)
+def factorial(number):
+    "compute factorial"
+
+    if number == 0:
+        return 1
+    else:
+        return number * factorial(number-1)
```

Aider's system prompt strongly encourages
GPT to produce this kind of high level diff, and provides a few examples.
GPT is much more successful at code editing
with the addition of this "high level diff" prompting.
It is better at producing correct diffs, which can be successfully
applied to the original file.

**Experiments without "high level diff" prompting
measure a 30-50% increase in editing errors,**
where diffs fail to apply or apply incorrectly and
produce invalid code.
Each such editing error causes a round trip back to GPT,
asking for better diffs.
These extra round trips slow down the pair programming experience
and increase token costs.

There are probably a couple of reasons why high level diffs
improve code editing performance:

- It is easier to produce diffs that both correctly match the original code and correctly produce the intended new code. There is less risk of getting confused while generating a rapid fire series of minimal, surgical edits mixed into existing code.
- The high level hunks often contain more lines than a surgical version, so they are less likely to accidentally match unrelated parts of the original file. This is important because GPT can't reliably give us line numbers to specify exactly where in the file to make the change.

### Be flexible when applying edits

GPT frequently makes errors when generating diffs, which
can prevent them from being correctly
applied as edits to the source files.
These imperfect diffs exhibit a variety of problems:

- GPT forgets to include some semantically irrelevant lines or details. Often GPT forgets things like comments, docstrings, blank lines, etc. Or it skips over some code that it doesn't intend to change.
- GPT forgets the leading *plus* `+` character to mark novel lines that it wants to add to the file, and incorrectly includes them with a leading *space* ` `.
- GPT jumps ahead to a new part of the file without starting a new hunk with a `@@ ... @@` divider.

As an example of the first issue, consider this source code:

```python
import sys

def main(args):
    # show a greeting

    print("Hello!")
    return

main(sys.argv[1:])
```

GPT might produce a unified diff like the one below,
which is missing the "show a greeting" comment line.
When we search for the *minus* `-` lines, we won't find them
in the original file
because of the missing comment.


```diff
@@ ... @@
-def main(args):
-
-    print("Hello!")
-    return
+def main(args):
+
+    print("Goodbye!")
+    return
```


Aider tries to be very flexible when applying unified diffs,
in order to handle all these sorts of defects.
If a hunk doesn't apply cleanly, aider uses a number of strategies
to try and apply the edit intended by GPT:

- Normalize the hunk, by taking the *minus* `-` and *space* ` ` lines as one version of the hunk and the *space* ` ` and *plus* `+` lines as a second version and doing an actual unified diff on them.
- Try and discover new lines that GPT is trying to add but which it forgot to mark with *plus* `+` markers. This is done by diffing the *minus* `-` and *space* ` ` lines back against the original file.
- Break a large hunk apart into an overlapping sequence of smaller hunks, which each contain only one contiguous run of *plus* `+` and *minus* `-` lines. Try and apply each of these sub-hunks independently.
- Vary the size and offset of the "context window" of *space* ` ` lines from the hunk that are used to localize the edit to a specific part of the file.
- Combine the above mechanisms to progressively become more permissive about how to apply the hunk.

These flexible patching strategies are critical to successfully apply the
unified diffs that GPT produces.
Removing support for flexible patching
radically increases the number of hunks which fail to apply.
Each such editing error causes a round trip back to GPT,
asking for better diffs.
These extra round trips slow down the pair programming experience
and increase token costs.

**Experiments where flexible patching is disabled** quantify the importance of this
feature:

- **GPT-4 Turbo's performance drops from 65% down to 56%** on the refactoring benchmark.
- **We see a 9X increase in editing errors** on aider's original Exercism benchmark.

## Conclusions and future work

Aider's new unified diff format seems very effective at stopping
GPT-4 Turbo from being a lazy coder.

I suspect that anyone who has tried to have GPT edit code
started out asking for diffs of some kind.
I know I did.
Any naive attempt to use actual unified diffs
or any other strict diff format
is certainly doomed,
but the techniques described here and
now incorporated into aider provide
a highly effective solution.

There could be significant benefits to
fine tuning models on
the simpler, high level style of diffs that are described here.
Dropping the line numbers and focusing on diffs of
semantically coherent chunks of code
seems to be an important part of successful GPT code editing.
Most LLMs will have already seen plenty of unified diffs
in their normal training data, and so should be
very amenable to fining tuning towards this
particular style of diff.
