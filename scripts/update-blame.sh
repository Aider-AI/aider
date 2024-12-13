#!/bin/bash

# exit when any command fails
set -e

# Use first argument as version if provided, otherwise default to v0.1.0
VERSION=${1:-v0.1.0}
./scripts/blame.py "$VERSION" --all --output aider/website/_data/blame.yml
