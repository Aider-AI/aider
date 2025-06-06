#!/bin/bash

# exit when any command fails
set -e

# Add verbosity flag to see more details about dependency resolution
VERBOSITY="-v"  # Use -v for less detail, -vvv for even more detail

# Attention: uv doesn't update to minor releases when output-file exists!

# First compile the common constraints of the full requirement suite
# to make sure that all versions are mutually consistent across files
rm requirements/common-constraints.txt
uv pip compile \
    $VERBOSITY \
    --no-strip-extras \
    --output-file=requirements/common-constraints.txt \
    requirements/requirements.in \
    requirements/requirements-*.in \
    $1

# Compile the base requirements
rm tmp.requirements.txt
uv pip compile \
    $VERBOSITY \
    --no-strip-extras \
    --constraint=requirements/common-constraints.txt \
    --output-file=tmp.requirements.txt \
    requirements/requirements.in \
    $1

{
  grep -v ^tree-sitter= tmp.requirements.txt
  echo; cat requirements/tree-sitter.in
  echo; cat requirements/pydub.in
} > requirements.txt

# Compile additional requirements files
SUFFIXES=(dev help browser playwright)

for SUFFIX in "${SUFFIXES[@]}"; do
    rm requirements/requirements-${SUFFIX}.txt
    uv pip compile \
        $VERBOSITY \
        --no-strip-extras \
        --constraint=requirements/common-constraints.txt \
        --output-file=requirements/requirements-${SUFFIX}.txt \
        requirements/requirements-${SUFFIX}.in \
        $1
done
