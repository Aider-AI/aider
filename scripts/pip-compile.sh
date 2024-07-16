#!/bin/bash

# exit when any command fails
set -e

pip-compile \
    requirements/requirements.in \
    --output-file=requirements.txt \
    $1

for SUFFIX in dev help browser playwright; do

    pip-compile \
        requirements/requirements-${SUFFIX}.in \
        --output-file=requirements/requirements-${SUFFIX}.txt \
        $1
done
    
