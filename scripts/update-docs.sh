#!/bin/bash

# exit when any command fails
set -e

if [ -z "$1" ]; then
  ARG=-r
else
  ARG=$1
fi

# README.md before index.md, because index.md uses cog to include README.md
cog $ARG \
    README.md \
    aider/website/index.md \
    aider/website/HISTORY.md \
    aider/website/docs/usage/commands.md \
    aider/website/docs/languages.md \
    aider/website/docs/config/dotenv.md \
    aider/website/docs/config/options.md \
    aider/website/docs/config/aider_conf.md \
    aider/website/docs/llms/other.md
