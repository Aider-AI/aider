#!/bin/bash

# exit when any command fails
set -e

# First compile the base requirements
pip-compile \
    --allow-unsafe \
    requirements/requirements.in \
    --output-file=requirements.txt \
    $1

# Then compile each additional requirements file in sequence
SUFFIXES=(dev help browser playwright)
CONSTRAINTS="--constraint=requirements.txt"

for SUFFIX in "${SUFFIXES[@]}"; do
    pip-compile \
        --allow-unsafe \
        requirements/requirements-${SUFFIX}.in \
        --output-file=requirements/requirements-${SUFFIX}.txt \
        ${CONSTRAINTS} \
        $1
    
    # Add this file as a constraint for the next iteration
    CONSTRAINTS+=" --constraint=requirements/requirements-${SUFFIX}.txt"
done
