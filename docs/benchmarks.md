
# GPT code editing benchmarks

Aider is a command line GPT chat tool that lets you ask for features, changes and
improvements to code in your local git repo.
I spend a lot of time trying to make aider better at this sort of chat driven AI code editing,
so that user chat requests are more likely to result in effective changes to their codebase.

Improving code editing involves tweaking and experimenting with 
the "edit format" part of the system prompt that aider uses.
The edit format specifies how GPT should format code edits in its reply,
and can range from simply "return an updated copy of the whole file" to
"use the 
[function calling API](https://openai.com/blog/function-calling-and-other-api-updates)
to specify a bunch of specific diffs".

Having a reliable way for GPT to read/modify/write source files is critical to
using GPT to code within an existing codebase.

To measure the impact of changes to the edit format,
I created a code editing benchmark based on the
[Exercism python](https://github.com/exercism/python)
coding exercises.
The benchmark measures how well aider & GPT can turn
a human coding request into
actual runnable code saved into files that passes unit tests.
This is an end-to-end assessment
of not just how well GPT can write code, but also how well it
can *edit existing code* and
*package up these code changes*
so that aider can save the edits to the
local source files.

I ran the benchmark
on almost all the ChatGPT models, using a variety of edit formats.
This produced some interesting observations:

  - Asking GPT to just return an updated copy of the whole file in a normal fenced code block is by far the most reliable edit format. This is true across all gpt-3.5 and gpt-4 models. Keeping the output format dead simple seems to leave GPT with more brain power to devote to the actual coding task. GPT is also less likely to mangle this simple output format.
  - Using the new function calling API is worse than the above whole file method, for all models. GPT writes worse code and frequently mangles this output format, even though OpenAI introduced the function calling API to make structured output formatting more reliable. This was a big surprise.
  - The new June (`0613`) versions of `gpt-3.5-turbo` are worse at code editing than the older Feb (`0301`) version. This was unexpected.
  - The gpt-4 models are much better at code editing than the gpt-3.5 models. This was expected.

These results agree with an intuition that I've been
developing about how to prompt GPT for complex tasks like coding.
You want to minimize the "cognitive load" of formatting the response, so that
GPT can focus on the task at hand.
You wouldn't expect a good result if you asked a junior developer to
implement a new feature by hand typing `diff -c` formatted updates to the current code.
I had hoped that the new function calling API would enable more reliable use of
structured output formats, but it does not appear to be a panacea
for code editing.

More details on the benchmark, edit formats and results are discussed below.

![benchmark results](../assets/benchmarks.svg)

## The benchmark

The benchmark uses 
[133 practice exercises from the Exercism python repository](https://github.com/exercism/python/tree/main/exercises/practice).
They were designed for people to learn and practice
their python coding skills.

Each exercise has:

  - Some brief instructions, in a markdown file.
  - A python implementation file, with a bare function or class that needs to be coded up.
  - Unit tests, contained in another python file.

The goal is to read the instructions, implement the provided functions/class skeletons
and pass all the unit tests. The benchmark measures what percentage of
the 133 exercises are completed successfully, with all the associated unit tests passing.

To complete an exercise, aider sends GPT the Exercism instructions followed by:

```
Use the above instructions to modify the supplied files: {file_list}
Keep and implement the existing function or class stubs, they will be called from unit tests.
Only use standard python libraries, don't suggest installing any packages.
```

Aider updates the implementation file based on GPT's reply and runs the unit tests.
If they all pass, we are done. If some tests fail, aider sends
the first 50 lines of test error output as a second message in the chat followed by:

```
See the testing errors above.
The tests are correct.
Fix the code in {file_list} to resolve the errors.
```

GPT gets this second chance to fix the implementation because
many of the unit tests check for specifics that are not
called out in the instructions.
For example, many tests want to see
[specific phrases in ValueErrors](https://github.com/exercism/python/blob/f6caa44faa8fb7d0de9a54ddb5c6183e027429c6/exercises/practice/queen-attack/queen_attack_test.py#L31)
raised by
the implementation.
There's no way for a human or an AI
to pass these unit tests
without seeing their error output.

It's worth noting that GPT never gets to see the source code of the unit tests.
Just the error output from failed tests.

## Editing formats

I benchmarked 4 different edit formats,
described below along with a sample of the response GPT might provide to the user request
"Change the print from hello to goodbye".

### whole

The
[whole](https://github.com/paul-gauthier/aider/blob/main/aider/coders/wholefile_prompts.py)
format asks GPT to just return the entire source file with any changes, formatted with normal markdown triple-backtick fences, inlined with the rest of its response text. This is how ChatGPT returns code snippets during normal chats.

````
Here is the updated copy of your file demo.py:

demo.py
```python
def main():
    print("goodbye")
```
````

### diff

The [diff](https://github.com/paul-gauthier/aider/blob/main/aider/coders/editblock_prompts.py)
format asks GPT to return edits in a simple diff format.
Each edit is a block of original and updated code, where GPT provides some original lines from the file and then a new replacement set of lines.

````
Here are the changes you requested to demo.py:

```python
demo.py
<<<<<<< ORIGINAL
    print("hello")
=======
    print("goodbye")
>>>>>>> UPDATED
```
````

### whole-func

The [whole-func](https://github.com/paul-gauthier/aider/blob/main/aider/coders/wholefile_func_coder.py) format requests whole files to be returned using the function call API.


```
{
    "explanation": "Changed hello to goodbye.",
    "files": [
        {
            "path": "demo.py",
            "content": "def main():\n    print(\"goodbye\")\n"
        }
}
```

### diff-func

The
[diff-func](https://github.com/paul-gauthier/aider/blob/main/aider/coders/editblock_func_coder.py)
format requests original/updated edits to be returned using the function call API.

```
{
    "explanation": "Changed hello to goodbye.",
    "edits": [
        {
            "path": "demo.py",
            "original_lines": [
                "    print(\"hello\")"
            ],
            "updated_lines": [
                "    print(\"goodbye\")"
            ],
        }
    ]
}       
```

## GPT-3.5 hallucinates function calls?

GPT-3.5 was very prone to ignoring the JSON Schema that specified valid functions,
and would often return a completely invalid `function_call` fragment with `"name": "python"`.

```
        "function_call": {
          "name": "python",
          "arguments": "def main():\n    print(\"hello\")\n"
        },
```

The `arguments` attribute is supposed to be a set of key/value pairs
with the arguments to the function specified in the `name` field.
Instead, gpt-3.5 frequently just stuffed the entire python
program into that field.

It feels like it might be getting confused by fine tuning that was done for ChatGPT plugins?

## Limitations

The OpenAI chat APIs are not deterministic, even at `temperature=0`.
The same identical request will produce multiple distinct responses,
usually on the order of 3-6 different variations. This feels
like they are load balancing across a number of slightly different
instances of the model.

For some exercises, some of these variable responses pass the unit tests while
other variants do not. Results for exercises like this which are
"on the bubble" 
are therefore a bit random, depending on which variant OpenAI returns.

Given that, it would be ideal to run all 133 exercises many times for each
model/edit-format combination and report an average performance.
This would average away the effect of the API variance.
It would also significantly increase the cost of this sort of benchmarking,
so I didn't do that.

Benchmarking against 133 exercises provides some robustness all by itself, since
we are measuring the performance across many exercises.

But to get a sense of how much the API variance impacts the benchmark outcomes,
I ran all 133 exercises 10 times each
against `gpt-3.5-turbo-0613` with the `whole` edit format.
You'll see one set of error bars in the graph, which demark
the range of results across those 10 runs.

The OpenAI API variance doesn't seem to
contribute to a large variance in the benchmark results.

## Conclusions

Based on these benchmarking results, aider will continue to use
`whole` for gpt-3.5 and `diff` for gpt-4.
While `gpt-4` gets slightly better results with the `whole` edit format,
it significantly increases costs and latency compared to `diff`.
Since `gpt-4` is already costly and slow, this seems like an acceptable
tradeoff.


