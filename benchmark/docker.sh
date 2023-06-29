#!/bin/bash

docker run \
       -it --rm \
       -v `pwd`:/aider \
       -v `pwd`/tmp.benchmarks/.:/benchmarks \
       -e OPENAI_API_KEY=$OPENAI_API_KEY \
       -e HISTFILE=/aider/.bash_history \
       aider-benchmark \
       bash
