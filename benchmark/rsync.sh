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

sync_repo() {
    # Sync the repository
    rsync -avz --delete \
          --exclude-from="$EXCLUDE_FILE" \
          "$REPO_ROOT/" \
          "$DEST:~/aider/" || sleep 0.1
    
    rsync -av .env .gitignore .aider.model.settings.yml "$DEST:~/aider/." || sleep 0.1

    echo Done syncing, waiting.
}
    
sync_repo

while true; do
    fswatch -o $REPO_ROOT | while read ; do
        sync_repo
    done
done
                              

# Clean up
rm "$EXCLUDE_FILE"

