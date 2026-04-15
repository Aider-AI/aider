#!/bin/bash

set -e

EXERCISES_DIR="$1"
BENCHMARK_DIR="$2"
shift 2

VOLUMES="-v $(pwd):/aider"

if [ -n "$EXERCISES_DIR" ] && [ -d "$EXERCISES_DIR" ]; then
    VOLUMES="$VOLUMES -v $(realpath "$EXERCISES_DIR"):/exercises:ro"
fi

if [ -n "$BENCHMARK_DIR" ] && [ -d "$BENCHMARK_DIR" ]; then
    VOLUMES="$VOLUMES -v $(realpath "$BENCHMARK_DIR"):/benchmarks:rw"
fi

ENV_VARS="-e AIDER_DOCKER=1 -e AIDER_BENCHMARK_DIR=/benchmarks -e HISTFILE=/aider/.bash_history"

if [ -n "$OPENAI_API_KEY" ]; then
    ENV_VARS="$ENV_VARS -e OPENAI_API_KEY=$OPENAI_API_KEY"
fi

if [ -n "$OPENAI_API_BASE" ]; then
    ENV_VARS="$ENV_VARS -e OPENAI_API_BASE=$OPENAI_API_BASE"
fi

exec docker run --rm --memory=12g --memory-swap=12g --add-host=host.docker.internal:host-gateway \
    $VOLUMES $ENV_VARS -w /aider aider-benchmark "$@"
