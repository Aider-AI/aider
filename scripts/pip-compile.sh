#!/bin/bash

# exit when any command fails
set -e

pip-compile requirements.in $1
pip-compile --output-file=requirements-dev.txt requirements-dev.in $1
pip-compile --output-file=requirements-hf-embed.txt requirements-hf-embed.in $1

