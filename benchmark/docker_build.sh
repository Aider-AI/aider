#!/bin/bash

set -e

docker build \
       --add-host=host.docker.internal:host-gateway \
       --file benchmark/Dockerfile \
       -t aider-benchmark \
       .
