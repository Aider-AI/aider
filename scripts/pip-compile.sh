#!/bin/bash

# exit when any command fails
set -e

# First compile the common constraints of the full requirement suite
# to make sure that all versions are mutually consistent across files
uv pip compile \
    --no-strip-extras \
    --output-file=requirements/common-constraints.txt \
    requirements/requirements.in \
    requirements/requirements-*.in \
    $1

# Compile the base requirements
uv pip compile \
    --no-strip-extras \
    --constraint=requirements/common-constraints.txt \
    --output-file=requirements.txt \
    requirements/requirements.in \
    $1

# Compile additional requirements files
SUFFIXES=(dev help browser playwright)

for SUFFIX in "${SUFFIXES[@]}"; do
    uv pip compile \
        --no-strip-extras \
        --constraint=requirements/common-constraints.txt \
        --output-file=requirements/requirements-${SUFFIX}.txt \
        requirements/requirements-${SUFFIX}.in \
        $1
done
