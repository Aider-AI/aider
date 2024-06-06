#!/bin/bash

# exit when any command fails
set -e

cog $ARG website/index.md
cog $ARG website/docs/usage.md
