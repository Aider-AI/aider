#!/bin/bash

# exit when any command fails
set -e

if [ -z "$1" ]; then
  ARG=-r
else
  ARG=$1
fi

cog $ARG \
    website/index.md \
    website/docs/commands.md \
    website/docs/languages.md \
    website/docs/options.md \
    website/docs/aider_conf.md
