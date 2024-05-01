#!/bin/bash

docker run \
       -it --rm \
       -v `pwd`:/aider \
       -v `pwd`/tmp.benchmarks/.:/benchmarks \
       -e OPENAI_API_KEY=$OPENAI_API_KEY \
       -e HISTFILE=/aider/.bash_history \
       -e AIDER_DOCKER=1 \
       -e AIDER_BENCHMARK_DIR=/benchmarks \
       -p 12345:12345 \
       aider-benchmark \
       bash
