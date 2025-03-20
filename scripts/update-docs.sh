#!/bin/bash

# exit when any command fails
set -e

if [ -z "$1" ]; then
  ARG=-r
else
  ARG=$1
fi

if [ "$ARG" != "--check" ]; then
  tail -1000 ~/.aider/analytics.jsonl > aider/website/assets/sample-analytics.jsonl
  cog -r aider/website/docs/faq.md
fi

# README.md before index.md, because index.md uses cog to include README.md
cog $ARG \
    README.md \
    aider/website/index.html \
    aider/website/HISTORY.md \
    aider/website/docs/usage/commands.md \
    aider/website/docs/languages.md \
    aider/website/docs/config/dotenv.md \
    aider/website/docs/config/options.md \
    aider/website/docs/config/aider_conf.md \
    aider/website/docs/config/adv-model-settings.md \
    aider/website/docs/config/model-aliases.md \
    aider/website/docs/leaderboards/index.md \
    aider/website/docs/leaderboards/edit.md \
    aider/website/docs/leaderboards/refactor.md \
    aider/website/docs/llms/other.md \
    aider/website/docs/more/infinite-output.md \
    aider/website/docs/legal/privacy.md
