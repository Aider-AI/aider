#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path
from aider.dump import dump

def get_lines_with_commit_hash(filename, aider_commits, verbose=False):
    result = subprocess.run(
        ["git", "blame", "-l", filename],
        capture_output=True,
        text=True,
        check=True
    )

    hashes = [
        line.split()[0]
        for line in result.stdout.splitlines()
    ]
    lines = Path(filename).read_text().splitlines()

    num_aider_lines = 0
    for hsh,line in zip(hashes, lines):
        if hsh in aider_commits:
            num_aider_lines += 1
            prefix = '+'
        else:
            prefix = " "

        if verbose:
            print(f"{prefix}{line}")

    num_lines = len(lines)

    return num_lines, num_aider_lines


def get_aider_commits():
    """Get commit hashes for commits with messages starting with 'aider:'"""
    commits = set()
    result = subprocess.run(
        ["git", "log", "--pretty=format:%H %s"],
        capture_output=True,
        text=True,
        check=True
    )

    for line in result.stdout.splitlines():
        commit_hash, commit_message = line.split(" ", 1)
        if commit_message.startswith("aider:"):
            commits.add(commit_hash)

    return commits



def process(fnames):
    aider_commits = get_aider_commits()
    for fname in fnames:
        get_lines_with_commit_hash(fname, aider_commits)

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <filename> ...")
        sys.exit(1)

    process(sys.argv[1:])


if __name__ == "__main__":
    main()
