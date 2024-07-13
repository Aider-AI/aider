#!/bin/bash

# exit when any command fails
set -e

pip-compile \
    requirements/requirements.in \
    --output-file=requirements.txt \
    $1

for SUFFIX in dev hf-embed ; do
    echo suffix: ${SUFFIX}
    pip-compile \
        requirements/requirements-${SUFFIX}.in \
        --output-file=requirements/requirements-${SUFFIX}.txt \
        $1
done
    
