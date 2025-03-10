#!/bin/bash

# exit when any command fails
set -e

# Add verbosity flag to see more details about dependency resolution
VERBOSITY="-v"  # Use -v for less detail, -vvv for even more detail

mkdir -p unfiltered

# Clean up temporary directory on exit
trap 'rm -f unfiltered/*.txt; rmdir unfiltered' EXIT

# First compile the common constraints of the full requirement suite
# to make sure that all versions are mutually consistent across files
uv pip compile \
    $VERBOSITY \
    --no-strip-extras \
    --output-file=unfiltered/common-constraints.txt \
    requirements/requirements.in \
    requirements/requirements-*.in \
    $1
scripts/block_requirements.py \
    unfiltered/common-constraints.txt \
    > requirements/common-constraints.txt

# Compile the base requirements
uv pip compile \
    $VERBOSITY \
    --no-strip-extras \
    --constraint=requirements/common-constraints.txt \
    --output-file=unfiltered/requirements.txt \
    requirements/requirements.in \
    $1
scripts/block_requirements.py unfiltered/requirements.txt \
    | cat - requirements/requirements.add/*.txt \
    > requirements.txt

# Compile additional requirements files
SUFFIXES=(dev help browser playwright)

for SUFFIX in "${SUFFIXES[@]}"; do
    uv pip compile \
        $VERBOSITY \
        --no-strip-extras \
        --constraint=requirements/common-constraints.txt \
        --output-file="unfiltered/requirements-${SUFFIX}.txt" \
        requirements/requirements-${SUFFIX}.in \
        $1
    scripts/block_requirements.py \
        "unfiltered/requirements-${SUFFIX}.txt" \
        | {
            if [[ -d "requirements/requirements-${SUFFIX}.add" ]]; then
                cat - "requirements/requirements-${SUFFIX}.add"/*.txt
            else
                cat
            fi
        } > "requirements/requirements-${SUFFIX}.txt"
done
