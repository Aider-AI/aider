---
title: GPT code editing benchmarks
excerpt: Benchmarking GPT-3.5 and GPT-4 code editing skill using a new code editing benchmark suite based on the Exercism python exercises.
highlight_image: /assets/benchmarks.jpg
nav_exclude: true
---
{% if page.date %}
<p class="post-date">{{ page.date | date: "%B %d, %Y" }}</p>
{% endif %}

# GPT code editing benchmarks

[![benchmark results](/assets/benchmarks.svg)](https://aider.chat/assets/benchmarks.svg)

Aider is an open source command line chat tool that lets you work with GPT to edit
code in your local git repo.
To do this, aider needs to be able to reliably recognize when GPT wants to edit local files,
determine which files it wants to modify and what changes to save.
Such automated
code editing hinges on using the system prompt
to tell GPT how to structure code edits in its responses.

Aider currently asks GPT to use simple text based "edit formats", but
[OpenAI's new function calling
API](https://openai.com/blog/function-calling-and-other-api-updates)
looks like a promising way to create more structured edit formats.
After implementing a couple of function based edit formats,
I wanted
to measure the potential benefits
of switching aider to use them by default.

With this in mind, I developed a
benchmark based on the [Exercism
python](https://github.com/exercism/python) coding exercises.
This
benchmark evaluates how effectively aider and GPT can translate a
natural language coding request into executable code saved into
files that pass unit tests.
It provides an end-to-end evaluation of not just
GPT's coding ability, but also its capacity to *edit existing code*
and *format those code edits* so that aider can save the
edits to the local source files.

I ran the benchmark
on all the ChatGPT models (except `gpt-4-32k`), using a variety of edit formats.
The results were interesting:

  - **Plain text edit formats worked best.** Asking GPT to return an updated copy of the whole file in a standard markdown fenced code block proved to be the most reliable and effective edit format across all GPT-3.5 and GPT-4 models. The results for this `whole` edit format are shown in solid blue in the graph.
  - **Function calls performed worse.** Using the new functions API for edits performed worse than the above whole file method, for all the models. GPT-3.5 especially produced inferior code and frequently mangled this output format. This was surprising, as the functions API was introduced to enhance the reliability of structured outputs. The results for these `...-func` edit methods are shown as patterned bars in the graph (both green and blue).
  - **The new June GPT-3.5 models did a bit worse than the old June model.** The performance of the new June (`0613`) versions of GPT-3.5 appears to be a bit worse than the February (`0301`) version. This is visible if you look at the "first attempt" markers on the first three solid blue bars and also by comparing the first three solid green `diff` bars.
  - **GPT-4 does better than GPT-3.5,** as expected.

The quantitative benchmark results agree with my intuitions
about prompting GPT for complex tasks like coding. It's beneficial to
minimize the "cognitive overhead" of formatting the response, allowing
GPT to concentrate on the coding task at hand.

As a thought experiment, imagine a slack conversation with a editor developer where
you ask them to write the code to add some new feature to your app.
They're going to type the response back to you by hand in the chat.
Should they type out the
code and wrap it in a normal markdown code block?
Or should they type up a properly escaped and
syntactically correct json data structure
that contains the text of the new code?

Using more complex output formats with GPT seems to cause two issues:

  - It makes GPT write worse code. Keeping the output format simple seems to allow GPT to devote more attention to the actual coding task.
  - It reduces GPT's adherence to the output format, making it more challenging for tools like aider to accurately identify and apply the edits GPT is attempting to make.

I was expecting to start using function call based edits in aider for both GPT-3.5 and GPT-4.
But given these benchmark results, I won't be adopting the functions API
at this time.
I will certainly plan to benchmark functions again with future versions of the models.

More details on the benchmark, edit formats and results are discussed below.


## The benchmark

The benchmark uses
[133 practice exercises from the Exercism python repository](https://github.com/exercism/python/tree/main/exercises/practice).
These
exercises were designed to help individuals learn Python and hone
their coding skills.

Each exercise includes:

  - [Instructions](https://github.com/exercism/python/blob/main/exercises/practice/anagram/.docs/instructions.md), provided in markdown files.
  - [Stub python code](https://github.com/exercism/python/blob/main/exercises/practice/anagram/anagram.py) in an *implementation file*, specifying the functions or classes that need to be implemented.
  - [Unit tests](https://github.com/exercism/python/blob/main/exercises/practice/anagram/anagram_test.py) in a separate python file.

The goal is for GPT to read the instructions, implement the provided function/class skeletons
and pass all the unit tests. The benchmark measures what percentage of
the 133 exercises are completed successfully, causing all the associated unit tests to pass.

To start each exercise, aider sends GPT
the initial contents of the implementation file,
the Exercism instructions
and a final instruction:

```
Use the above instructions to modify the supplied files: <implementation file>
Keep and implement the existing function or class stubs, they will be called from unit tests.
Only use standard python libraries, don't suggest installing any packages.
```

Aider updates the implementation file based on GPT's reply and runs
the unit tests. If all tests pass, the exercise is considered
complete. If some tests fail, aider sends GPT a second message with
the test error output. It only sends the first 50 lines of test errors
to try and avoid exceeding the context window of the smaller models. Aider
also includes this final instruction:

```
See the testing errors above.
The tests are correct.
Fix the code in <implementation file> to resolve the errors.
```

Requiring GPT to fix its first implementation in response to test failures
is another way in which this benchmark stresses code editing skill.
This second chance is also important because it
gives GPT the opportunity to adjust if the
instructions were imprecise with respect to the
specific requirements of the unit tests.
Many of the exercises have multiple paragraphs of instructions,
and most human coders would likely fail some tests on their
first try.

The bars in the graph show the percent of exercises that were completed by
each model and edit format combination. The full bar height represents
the final outcome following both coding attempts.
Each bar also has a horizontal mark that shows
the intermediate performance after the first coding attempt,
without the benefit of the second try that includes the test error output.

It's worth noting that GPT never gets to see the source code of the
unit tests during the benchmark. It only sees the error output from
failed tests. Of course, all of this code was probably part of its
original training data!

In summary, passing an exercise means GPT was able to:

  - Write the required code (possibly after reviewing test error output),
  - Correctly package all of the code edits into the edit format so that aider can process and save it to the implementation file.

Conversely, failing an exercise only requires a breakdown in one of
those steps. In practice, GPT fails at different steps in different
exercises. Sometimes it simply writes the wrong code. Other times, it
fails to format the code edits in a way that conforms to the edit
format, resulting in the code not being saved correctly.

It's worth keeping in mind that changing the edit format often affects
both aspects of GPT's performance.
Complex edit formats often lead GPT to write worse code *and* make it less
successful at formatting the edits correctly.


## Edit formats

I benchmarked 4 different edit formats, described below.
Each description includes a sample response that GPT might provide to a user who
requests:
"Change the print from hello to goodbye."

### whole

The
[whole](https://github.com/Aider-AI/aider/blob/main/aider/coders/wholefile_prompts.py)
format asks GPT to return an updated copy of the entire file, including any changes.
The file should be
formatted with normal markdown triple-backtick fences, inlined with the rest of its response text.

This format is very similar to how ChatGPT returns code snippets during normal chats, except with the addition of a filename right before the opening triple-backticks.

````
Here is the updated copy of your file demo.py:

demo.py
```python
def main():
    print("goodbye")
```
````

### diff

The [diff](https://github.com/Aider-AI/aider/blob/main/aider/coders/editblock_prompts.py)
format also asks GPT to return edits as part of the normal response text,
in a simple diff format.
Each edit is a fenced code block that
specifies the filename and a chunk of ORIGINAL and UPDATED code.
GPT provides some original lines from the file and then a new updated set of lines.

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

The [whole-func](https://github.com/Aider-AI/aider/blob/main/aider/coders/wholefile_func_coder.py)
format requests updated copies of whole files to be returned using the function call API.


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
[diff-func](https://github.com/Aider-AI/aider/blob/main/aider/coders/editblock_func_coder.py)
format requests a list of
original/updated style edits to be returned using the function call API.

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

## GPT-3.5's performance

### The `0613` models seem worse?

The GPT-3.5 benchmark results have me fairly convinced that the new
`gpt-3.5-turbo-0613` and `gpt-3.5-16k-0613` models
are a bit worse at code editing than
the older `gpt-3.5-turbo-0301` model.

This is visible in the "first attempt"
portion of each result, before GPT gets a second chance to edit the code.
Look at the horizontal white line in the middle of the first three blue bars.
Performance with the `whole` edit format was 46% for the
February model and only 39% for the June models.

But also note how much the solid green `diff` bars
degrade between the February and June GPT-3.5 models.
They drop from 30% down to about 19%.

I saw other signs of this degraded performance
in earlier versions of the
benchmark as well.

### Pathological use of `diff`

When GPT-3.5 is able to correctly generate the `diff` edit format,
it often uses it in a pathological manner. It places the *entire*
original source file in the ORIGINAL block and the entire updated file
in the UPDATED block. This is strictly worse than just using the
`whole` edit format, as GPT is sending two full copies of the file.

### Hallucinated function calls

When GPT-3.5 uses the functions API
it is prone to ignoring the JSON Schema that specifies valid functions.
It often returns a completely novel and semantically
invalid `function_call` fragment with `"name": "python"`.

The `arguments` attribute is supposed to be a set of key/value pairs
with the arguments to the function specified in the `name` field.
Instead, GPT-3.5 frequently just stuffs an entire python
file into that field.

```
        "function_call": {
          "name": "python",
          "arguments": "def main():\n    print(\"hello\")\n"
        },
```

It seems like it might be getting confused by fine-tuning that was
done for the ChatGPT code interpreter plugin?




## Randomness

The benchmark attempts to be deterministic, always sending identical
requests for each exercise on repeated runs.
As part of this effort,
when sending test error output to GPT,
it removes the wall-clock timing information that
is normally included by the `unittest` module.

The benchmark harness also logs SHA hashes of
all the OpenAI API requests and replies.
This makes it possible to
detect randomness or nondeterminism
in the benchmarking process.

It turns out that the OpenAI chat APIs are not deterministic, even at
`temperature=0`.  The same identical request will produce multiple
distinct responses, usually less than 5-10 variations.  This suggests
that OpenAI may be load balancing their API across a number of
slightly different instances of the model?

For certain exercises, some of these variable responses pass the unit tests while
other variants do not. Results for exercises like this, which are
"on the bubble",
are therefore a bit random, depending on which variant OpenAI returns.

Given that, it would be ideal to run all 133 exercises many times for each
model/edit-format combination and report an average performance.
This would average away the effect of the API variance.
It would also significantly increase the cost of this sort of benchmarking.
So I didn't do that.

Benchmarking against 133 exercises already provides some robustness, since
we are measuring the performance across many exercises.

But to get a sense of how much the API variance impacts the benchmark outcomes,
I ran all 133 exercises 10 times each
against `gpt-3.5-turbo-0613` with the `whole` edit format.
You'll see one set of error bars in the graph, which show
the range of results from those 10 runs.

The OpenAI API randomness doesn't seem to
cause a large variance in the overall benchmark results.

## Conclusions

Based on these benchmark results, aider will continue to use
the `whole` edit format for GPT-3.5, and `diff` for GPT-4.

GPT-4 gets comparable results with the `whole` and `diff` edit formats,
but using `whole` significantly increases costs and latency compared to `diff`.

The latency of streaming back the entire updated copy of each edited file
is a real challenge with the `whole` format.
The GPT-3.5 models are quite responsive, and can
stream back entire files at reasonable speed.
Aider displays a progress bar and
live diffs of the files as they stream in,
which helps pass the time.

The GPT-4 models are much slower, and waiting for even small files
to be completely "retyped" on each request is probably unacceptable.
