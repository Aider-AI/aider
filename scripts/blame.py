#!/usr/bin/env python3

import sys
import subprocess
from aider.dump import dump

def get_aider_commits():
    """Get commit hashes for commits with messages starting with 'aider:'"""
    commits = []
    result = subprocess.run(
        ["git", "log", "--pretty=format:%H %s"],
        capture_output=True,
        text=True,
        check=True
    )

    for line in result.stdout.splitlines():
        print(line)
        commit_hash, commit_message = line.split(" ", 1)
        if commit_message.startswith("aider:"):
            commits.append(commit_hash)

    return commits



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <filename>")
        sys.exit(1)

    mark_aider_lines(sys.argv[1])
