#!/usr/bin/env python3

import subprocess
import sys
import tempfile
from pathlib import Path
from aider.dump import dump

def get_all_commit_hashes_since_tag(tag):
    try:
        # Get all commit hashes since the specified tag
        result = subprocess.run(
            ["git", "rev-list", f"{tag}..HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        # Split the output into individual commit hashes
        commit_hashes = result.stdout.strip().split('\n')
        return commit_hashes
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}", file=sys.stderr)
        return []

def main():
    pass

if __name__ == "__main__":
    main()
