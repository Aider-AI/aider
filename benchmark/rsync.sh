#!/bin/bash

set -e

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

# Create remote directory if needed
ssh "$DEST" "mkdir -p ~/aider"

# Sync the repository
rsync -avz --delete \
    --exclude-from="$EXCLUDE_FILE" \
    "$REPO_ROOT/" \
    "$DEST:~/aider/"

rsync -a .env .bash_history .gitignore "$DEST:~/aider/."

rsync -a ~/dotfiles/screenrc "$DEST:.screenrc"

# Clean up
rm "$EXCLUDE_FILE"
