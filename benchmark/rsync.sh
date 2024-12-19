#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 user@host"
    exit 1
fi

DEST="$1"
REPO_ROOT="$(git rev-parse --show-toplevel)"

# Create a temporary file for rsync exclude patterns
EXCLUDE_FILE=$(mktemp)

# Convert .gitignore patterns to rsync exclude patterns
git -C "$REPO_ROOT" ls-files --exclude-standard --others --ignored --directory > "$EXCLUDE_FILE"

# make ~/aider on the remote side if needed ai!

# Sync the repository
rsync -avz --delete \
    --exclude='.git/' \
    --exclude-from="$EXCLUDE_FILE" \
    "$REPO_ROOT/" \
    "$DEST:~/aider/"

# Clean up
rm "$EXCLUDE_FILE"
