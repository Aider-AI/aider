
# Code editing benchmarks

Aider is a command line GPT chat tool that lets you ask for features, changes and
improvements to code in your local git repo.
I spend a lot of time trying to make aider better at this sort of chat driven AI code editing,
so that user chat requests are more likely to result in effective changes to their codebase.
In order to improve something, it really helps to have metrics to measure progress.

So I created a code editing benchmark based on the
[Exercism python]()
coding exercises
to measure the impact of changes to aider.
I am especially interested in assessing changes to the "edit format", which is:

  - The *system prompt* that aider sends along with user requests, which specifies how GPT should format the code edits in its reply (as json data, fenced markdown, function_calls, etc). 
  - The *editing backend* in aider which processes code edits found in GPT replies and applies
them to the local source files. This includes the not uncommon case where GPT ignores the system prompt and returns poorly formatted replies.

The benchmark is measuring how well aider & GPT can turn a human request into
actual runnable source code saved into files that passes unit tests.
This is an end-to-end assessment
of not just how well GPT can write code, but also how well it
package up and format these code changes
so that aider can save edits to the
local source files.
Having a reliable automated way for GPT to read/modify/write source files is critical to
efficiently coding with GPT within an existing codebase.

I ran the benchmark
across many different ChatGPT models using a variey of different edit formats.
This produced somem interesting observations, some of which were surprising:

  - Asking GPT to just return the whole file (including changes) as a fenced code block within it's normal markdown response is by far the most reliable way to have it edit code. This is true across all gpt-3.5 and gpt-4 models. Keeping the output format dead simple seems to leave GPT with more brain power to devote to the actual coding task. It is also less likely to mangle this simple output format.
  - Using the new `function_call` API is worse than returning whole files in markdown. GPT writes worse code and frequently mangles the output format, even though OpenAI introduced the `function_call` API to make structured output formatting more reliable. This was a big surprise.
  - The new June (`0613`) versions of `gpt-3.5-turbo` are worse at code editing than the older Feb (`0301`) version. This was unexpected.
  - The gpt-4 models are much better at code editing than the gpt-3.5 models. This was expected, based on my hands on experience using aider to edit code with both models.

These results agree with a key intuition that I've been
developing about how to prompt GPT for complex tasks like coding.
You want to minimize the "cognitive load" of formatting the response, so that
GPT can focus on the task at hand.
You wouldn't expect a good result if you asked a junior developer to
implement a new feature by hand typing `diff -c` syntax diffs against the current code.
I had hoped that the new `function_call` API would enable more reliable use of
structured output formats, but it does not appear to be a panacea
for the code editing task.

More details on the benchmark, edit formats and results are discussed below.

## The benchmark

The benchmark uses the 133
[practice exercises from the Exercism python repository](https://github.com/exercism/python/tree/main/exercises/practice).
They were designed for people to learn and practice
their python coding skills.

Each exercise has:

  - Some brief instructions, in a markdown file.
  - The implementation file, which is a python file with a bare function or class that needs to be coded up.
  - Unit tests, contained in another python file.

The goal is to read the instructions, implement the functions/classes provided
and pass all the unit tests. The benchmark measures what percentage of
the 133 exercises are completed successfully, with all the associated unit tests passing.

To run the test, aider sends GPT the Exercism instructions followed by:

> Use the above instructions to modify the supplied files: {file_list}
> Keep and implement the existing function or class stubs, they will be called from unit tests.
> Only use standard python libraries, don't suggest installing any packages.

Aider updates the implementation file based on GPT's reply and runs the unit tests.
If they all pass, we are done. If some tests fail, aider sends
the first 50 lines of test error output as a second message in the chat followed by:

> See the testing errors above.
> The tests are correct.
> Fix the code in {file_list} to resolve the errors.

GPT gets this second chance to fix the implementation because
many of the unit tests check for specifics that are not
clearly called out in the instructions.
For example, many tests want to see
[specific phrases in ValueErrors](https://github.com/exercism/python/blob/f6caa44faa8fb7d0de9a54ddb5c6183e027429c6/exercises/practice/queen-attack/queen_attack_test.py#L31)
raised by
the implementation.
There's no way for a human or an AI
to pass these unit tests
without seeing their error output.

It's worth noting that GPT never gets to see the source code of the unit tests.
Just the error output from failed tests.

If you look closely at the bar graph of results, you'll see each column is divided
in two by a small horizontal line. That line marks the percentage of
exercises that fully passed their tests on the first try, without
any need to show GPT test error output.
Again, no human could ever pass 100% of the tests in one try, because
the unit tests are overly specific about arbitrary things like error
message text.

# Editing formats

I benchmarked 4 different edit formats:

  - [whole](https://github.com/paul-gauthier/aider/blob/main/aider/coders/wholefile_prompts.py#L17) which asks GPT to just return the entire source file with any changes, formatted with normal markdown triple-backtick fences, inlined with the rest of its response text. This is how ChatGPT is used to return small code snippets during normal chats.
  - [diff](https://github.com/paul-gauthier/aider/blob/main/aider/coders/editblock_prompts.py) which asks GPT to return edits in a simple diff format. Each edit is a block of original and updated code, where GPT provides some original lines from the file and then a new replacement set of lines.
  - [whole-func](https://github.com/paul-gauthier/aider/blob/main/aider/coders/wholefile_func_coder.py) which requests whole files to be returned using the function call API.
  - [diff-func](https://github.com/paul-gauthier/aider/blob/main/aider/coders/editblock_func_coder.py) which requests original/updated edits to be returned using the function call API.


# ChatGPT function calls

# Limitations

# Conclusions

Aider uses `whole` for gpt-3.5 and `diff` for gpt-4.

