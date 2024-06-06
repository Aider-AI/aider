#!/bin/bash

# exit when any command fails
set -e

if [ -z "$1" ]; then
  ARG=-r
else
  ARG=$1
fi

cog $ARG website/index.md
cog $ARG website/docs/usage.md
