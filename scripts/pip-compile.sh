#!/bin/bash

# exit when any command fails
set -e

# First compile the base requirements
pip-compile \
    requirements/requirements.in \
    --output-file=requirements.txt \
    $1

# Then compile each additional requirements file in sequence,
# using the previous requirements as constraints
pip-compile \
    requirements/requirements-dev.in \
    --output-file=requirements/requirements-dev.txt \
    --constraint=requirements.txt \
    $1

pip-compile \
    requirements/requirements-help.in \
    --output-file=requirements/requirements-help.txt \
    --constraint=requirements.txt \
    --constraint=requirements/requirements-dev.txt \
    $1

pip-compile \
    requirements/requirements-browser.in \
    --output-file=requirements/requirements-browser.txt \
    --constraint=requirements.txt \
    --constraint=requirements/requirements-dev.txt \
    --constraint=requirements/requirements-help.txt \
    $1

pip-compile \
    requirements/requirements-playwright.in \
    --output-file=requirements/requirements-playwright.txt \
    --constraint=requirements.txt \
    --constraint=requirements/requirements-dev.txt \
    --constraint=requirements/requirements-help.txt \
    --constraint=requirements/requirements-browser.txt \
    $1
    
