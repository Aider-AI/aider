#!/bin/bash

# exit when any command fails
set -e

cog -r website/index.md
cog -r website/docs/usage.md
