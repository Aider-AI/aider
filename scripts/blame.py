#!/usr/bin/env python3

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

import sys

def mark_aider_lines(filename):
    aider_commits = set(get_aider_commits())
    
    with open(filename, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines, start=1):
        result = subprocess.run(
            ["git", "blame", "-L", f"{i},{i}", "--porcelain", filename], 
            capture_output=True,
            text=True,
            check=True
        )
        commit_hash = result.stdout.split(" ")[0]
        if commit_hash in aider_commits:
            print(f"* {line}", end="")
        else:
            print(f"  {line}", end="")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <filename>")
        sys.exit(1)
        
    mark_aider_lines(sys.argv[1])
