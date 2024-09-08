#!/bin/bash

# Example of a callback script in bash for Aider.

SCRIPT_DIR=$(cd $(dirname $0); pwd)
PARAMS=$1
PROJECT=$(echo "$PARAMS" | jq -r '.root')

echo "$PARAMS" > ${SCRIPT_DIR}/aider_callback_params.json

# if macos, notify
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e "display notification \"Aider has finished processing $PROJECT\" with title \"Aider\" sound name \"default\""
fi
