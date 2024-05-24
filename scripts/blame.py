#!/usr/bin/env python3

import sys
import subprocess
from aider.dump import dump

def get_lines_with_commit_hash(filename):
    result = subprocess.run(
        ["git", "blame", "-l", filename],
        capture_output=True,
        text=True,
        check=True
    )

    lines_with_hash = []
    commit_hash = None

    hashes = [
        line.split[0]
        for line in result.stdout.splitlines()
    ]
    lines = Path(filename).splitlines()


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

    get_lines_with_commit_hash(sys.argv[1])
