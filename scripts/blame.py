#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import argparse
from pathlib import Path
from aider.dump import dump


def get_all_commit_hashes_since_tag(tag):
    res = run(["git", "rev-list", f"{tag}..HEAD"])

    if res:
        commit_hashes = res.strip().split('\n')
        return commit_hashes

def run(cmd):
    try:
        # Get all commit hashes since the specified tag
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

def get_commit_authors(commits):
    commit_to_author = dict()


def main():
    parser = argparse.ArgumentParser(description="Get commit hashes since a specified tag.")
    parser.add_argument("tag", help="The tag to start from")
    args = parser.parse_args()

    commits = get_all_commit_hashes_since_tag(args.tag)
    commits = [commit[:len('44e6fefc2')] for commit in commits]
    dump(commits)

    authors = get_commit_authors(commits)


    #text = run(['git', 'blame', f'{args.tag}..HEAD', '--', 'aider/main.py'])
    #text = text.splitlines()



if __name__ == "__main__":
    main()
