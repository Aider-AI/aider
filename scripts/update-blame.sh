#!/bin/bash

# exit when any command fails
set -e

# take a version as an optional command line arg; use v0.1.0 if not provided AI!
./scripts/blame.py v0.1.0 --all --output aider/website/_data/blame.yml
