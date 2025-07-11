#!/bin/bash

VOLUME_LABEL=""

if [ -f "/usr/bin/getenforce" ]; then
  if [ "$(/usr/bin/getenforce)" == "Enforcing" ]; then
    VOLUME_LABEL=":Z"
  fi
fi

docker run \
       -it --rm \
       --memory=12g \
       --memory-swap=12g \
       --add-host=host.docker.internal:host-gateway \
       -v `pwd`:/aider$VOLUME_LABEL \
       -v `pwd`/tmp.benchmarks/.:/benchmarks$VOLUME_LABEL \
       -e OPENAI_API_KEY="$OPENAI_API_KEY" \
       -e HISTFILE=/aider/.bash_history \
       -e PROMPT_COMMAND='history -a' \
       -e HISTCONTROL=ignoredups \
       -e HISTSIZE=10000 \
       -e HISTFILESIZE=20000 \
       -e AIDER_DOCKER=1 \
       -e AIDER_BENCHMARK_DIR=/benchmarks \
       aider-benchmark \
       bash
