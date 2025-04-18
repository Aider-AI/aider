#!/bin/bash

# This runs docker with localhost mapped to the host-gateway for convenience.
# This allows default ENV to work for configuration such as Ollama endponts.
docker run \
       -it --rm \
       --memory=25g \
       --memory-swap=25g \
       --env-file .env \
       --add-host=localhost:host-gateway \
       -v `pwd`:/aider \
       -v `pwd`/tmp.benchmarks/.:/benchmarks \
       -e HISTFILE=/aider/.bash_history \
       -e PROMPT_COMMAND='history -a' \
       -e HISTCONTROL=ignoredups \
       -e HISTSIZE=10000 \
       -e HISTFILESIZE=20000 \
       -e AIDER_DOCKER=1 \
       -e AIDER_BENCHMARK_DIR=/benchmarks \
       aider-benchmark \
       bash
