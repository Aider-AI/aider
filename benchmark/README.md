
# Aider code editing benchmark harness

Aider uses a "code editing" benchmark to quantitatively measure how well it works
with the GPT-3.5 and GPT-4 models.
This directory holds the harness and tools needed to run the benchmarking suite.

## Background

The benchmark is based on the [Exercism
python](https://github.com/exercism/python) coding exercises.
This
benchmark evaluates how effectively aider and GPT can translate a
natural language coding request into executable code saved into
files that pass unit tests.
It provides an end-to-end evaluation of not just
GPT's coding ability, but also its capacity to *edit existing code*
and *format those code edits* so that aider can save the
edits to the local source files.

See [this writeup for a longer discussion about the benchmark and how to interpret the results](https://aider.chat/docs/benchmarks.html).

The benchmark is intended to be run *inside a docker container*.
This is because the benchmarking harness will be
taking code written by an LLM
and executing it without any human review or supervision!
The LLM could generate dangerous python that harms your system, like this: `import os; os.system("sudo rm -rf /")`.
Running inside a docker container helps limit the damage that could be done.

## Usage

There are 3 main tasks involved in benchmarking aider:

1. Install and setup for benchmarking.

2. Run the benchmark to measure performance across the 133 exercises.

3. Generate a summary report of how many of the exercises succeeded or failed.

### Setup for benchmarking

First, prepare all the groundwork for running the benchmarks.
These steps only need to be done once.

```
# Clone the aider repo
git clone git@github.com:paul-gauthier/aider.git

# Create the scratch dir to hold benchmarking results inside the main aider dir:
cd aider
mkdir tmp.benchmarks

# Clone the exercism repo
git clone git@github.com:exercism/python.git

# Copy the practice exercises into the benchmark scratch dir
cp -rp python/exercises/practice tmp.benchmarks/practice

# Build the docker container
./benchmark/docker_build.sh
```

### Running the benchmark

Launch the docker container and run the benchmark inside it:

```
# Launch the docker container
./benchmark/docker.sh

# Inside the container, install aider as a development build.
# This way you're running the code that you cloned above, including any local changes.
pip install -e .

# Run the benchmark:
./benchmark/benchmark.py a-helpful-name-for-this-run --model gpt-3.5-turbo --edit-format whole --threads 10
```

The above will create a folder `tmp.benchmarks/YYYY-MM-DD-HH-MM-SS--a-helpful-name-for-this-run` with benchmarking results.
Run like this, the script will run all 133 exercises in a random order.

You can run `./benchmark/benchmark.py --help` for a list of all the arguments, but here are the most useful to keep in mind:

- `--model` is the name of the model, same as you would pass directly to `aider`.
- `--edit-format` is the name of the edit format, same as you would pass directly to `aider`. When working with an experimental LLM, I recommend starting with `whole`
- `--threads` specifies how many exercises to benchmark in parallel. Start with a single thread if you are working out the kinks on your benchmarking setup or working with a new model, etc. Once you are getting reliable results, you can speed up the process by running with more threads. 10 works well against the OpenAI APIs.
- `--num-tests` specifies how many of the 133 tests to run before stopping. This is another way to start gently as you debug your benchmarking setup.
- `--keywords` filters the tests to run to only the ones whose name match the supplied argument (similar to `pytest -k xxxx`).

### Generating a benchmark report

You can generate stats about any benchmark, including ones which are still running.
You don't need to run this inside the docker container, as it is just
collecting stats not executing unsafe python.

```
# Generate stats for a specific benchmarking directory
./benchmark/benchmark.py --stats tmp.benchmarks/YYYY-MM-DD-HH-MM-SS--a-helpful-name-for-this-run
```

## Limitations, notes

- If you're experimenting with non-OpenAI models, the benchmarking harness may not provide enough switches/control to specify the integration to such models. You probably need to edit `benchmark.py` to instantiate `Coder()` appropriately. You can just hack this in or add new switches/config.
- Benchmarking all 133 exercises against GPT-4 will cost about $10-20.
- Benchmarking aider is intended for folks who are actively developing aider or doing experimental work adapting it for use with [new LLM models](https://github.com/paul-gauthier/aider/issues/172).
- These scripts are not intended for use by typical aider users.
- Some of the tools are written as `bash` scripts, so it will be hard to use them on Windows.
