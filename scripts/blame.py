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
    total_lines = 0
    total_aider_lines = 0

    for fname in fnames:
        num_lines, num_aider_lines = get_lines_with_commit_hash(fname, aider_commits)
        total_lines += num_lines
        total_aider_lines += num_aider_lines
        percent_modified = (num_aider_lines / num_lines) * 100 if num_lines > 0 else 0
        print(f"{fname}: {num_aider_lines}/{num_lines} lines modified by aider ({percent_modified:.2f}%)")

    total_percent_modified = (total_aider_lines / total_lines) * 100 if total_lines > 0 else 0
    print(f"Total: {total_aider_lines}/{total_lines} lines modified by aider ({total_percent_modified:.2f}%)")

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <filename> ...")
        sys.exit(1)

    process(sys.argv[1:])


if __name__ == "__main__":
    main()
