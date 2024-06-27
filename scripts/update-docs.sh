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
    website/index.md \
    website/HISTORY.md \
    website/docs/commands.md \
    website/docs/languages.md \
    website/docs/config/dotenv.md \
    website/docs/config/options.md \
    website/docs/config/aider_conf.md
