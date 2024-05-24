#!/usr/bin/env python3

import sys
import subprocess
from aider.dump import dump

def get_lines_with_commit_hash(filename):
    result = subprocess.run(
        ["git", "blame", "--line-porcelain", filename],
        capture_output=True,
        text=True,
        check=True
    )

    lines_with_hash = []
    commit_hash = None
    line_content = None

    for line in result.stdout.splitlines():
        if line.startswith("author "):
            pass
        elif line.startswith("committer "):
            pass 
        elif line.startswith("summary "):
            pass
        elif line.startswith("previous "):
            pass
        elif line.startswith("filename "):
            pass
        elif line.startswith("\t"):
            line_content = line[1:]
        elif line.startswith("boundary"):
            pass
        else:
            commit_hash = line.split(" ")[0]
            if commit_hash and line_content:
                lines_with_hash.append(f"{commit_hash}: {line_content}")
            line_content = None

    return lines_with_hash

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
