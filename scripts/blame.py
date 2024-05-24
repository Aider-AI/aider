#!/usr/bin/env python3

import subprocess
import sys
import tempfile
from pathlib import Path

import pylab as plt
from imgcat import imgcat

from aider.dump import dump


def get_lines_with_commit_hash(filename, aider_commits, git_dname, verbose=False):
    result = subprocess.run(
        ["git", "-C", git_dname, "blame", "-w", "-l", filename],
        capture_output=True,
        text=True,
        check=True,
    )

    hashes = [line.split()[0] for line in result.stdout.splitlines()]
    lines = Path(filename).read_text().splitlines()

    num_aider_lines = 0
    for hsh, line in zip(hashes, lines):
        if hsh in aider_commits:
            num_aider_lines += 1
            prefix = "+"
        else:
            prefix = " "

        if verbose:
            print(f"{prefix}{line}")

    num_lines = len(lines)

    return num_lines, num_aider_lines


def get_aider_commits(git_dname):
    """Get commit hashes for commits with messages starting with 'aider:'"""

    result = subprocess.run(
        ["git", "-C", git_dname, "log", "--pretty=format:%H %s"],
        capture_output=True,
        text=True,
        check=True,
    )

    results = result.stdout.splitlines()
    dump(len(results))

    commits = set()
    for line in results:
        commit_hash, commit_message = line.split(" ", 1)
        if commit_message.startswith("aider:"):
            commits.add(commit_hash)

    dump(len(commits))

    return commits


def show_commit_stats(commits):
    total_added_lines = 0
    total_deleted_lines = 0

    for commit in commits:
        result = subprocess.run(
            ["git", "show", "--stat", "--oneline", commit],
            capture_output=True,
            text=True,
            check=True,
        )

        added_lines = 0
        deleted_lines = 0
        for line in result.stdout.splitlines():
            if "changed," not in line:
                continue
            if "insertion" not in line and "deletion" not in line:
                continue
            dump(line)
            pieces = line.split(",")
            try:
                for piece in pieces:
                    if "insertion" in piece:
                        dump(piece)
                        added_lines += int(piece.strip().split()[0])
                    if "deletion" in piece:
                        dump(piece)
                        deleted_lines += int(piece.strip().split()[0])
            except ValueError:
                pass

        total_added_lines += added_lines
        total_deleted_lines += deleted_lines

        print(f"Commit {commit}: +{added_lines} -{deleted_lines}")

    print(f"Total: +{total_added_lines} -{total_deleted_lines}")


def process_fnames(fnames, git_dname):
    if not git_dname:
        git_dname = "."

    aider_commits = get_aider_commits(git_dname)
    # show_commit_stats(aider_commits)

    total_lines = 0
    total_aider_lines = 0

    for fname in fnames:
        num_lines, num_aider_lines = get_lines_with_commit_hash(fname, aider_commits, git_dname)
        total_lines += num_lines
        total_aider_lines += num_aider_lines
        percent_modified = (num_aider_lines / num_lines) * 100 if num_lines > 0 else 0
        if not num_aider_lines:
            continue
        print(f"|{fname}| {num_aider_lines} of {num_lines} | {percent_modified:.1f}% |")

    total_percent_modified = (total_aider_lines / total_lines) * 100 if total_lines > 0 else 0
    print(
        f"| **Total** | **{total_aider_lines} of {total_lines}** | {total_percent_modified:.1f}% |"
    )
    return total_aider_lines, total_lines, total_percent_modified


def process_repo(git_dname=None):
    if not git_dname:
        git_dname = "."

    result = subprocess.run(
        ["git", "-C", git_dname, "ls-files"], capture_output=True, text=True, check=True
    )
    git_dname = Path(git_dname)
    fnames = [git_dname / fname for fname in result.stdout.splitlines() if fname.endswith(".py")]

    return process_fnames(fnames, git_dname)


def history():
    git_dname = "."
    result = subprocess.run(
        ["git", "-C", git_dname, "log", "--pretty=format:%H %s"],
        capture_output=True,
        text=True,
        check=True,
    )

    commits = []
    for line in result.stdout.splitlines():
        commit_hash, commit_message = line.split(" ", 1)
        commits.append(commit_hash)

    commits.reverse()
    dump(len(commits))

    num_commits = len(commits)
    N = 10
    step = (num_commits - 1) / (N - 1)
    results = []
    i = 0
    while i < num_commits:
        commit_num = int(i)
        dump(i, commit_num, num_commits)
        i += step

        commit = commits[commit_num]

        repo_dname = tempfile.TemporaryDirectory().name
        cmd = f"git clone . {repo_dname}"
        subprocess.run(cmd.split(), check=True)
        dump(commit)
        cmd = f"git -c advice.detachedHead=false -C {repo_dname} checkout {commit}"
        subprocess.run(cmd.split(), check=True)

        aider_lines, total_lines, pct = process_repo(repo_dname)
        results.append((commit_num, aider_lines, total_lines, pct))

    dump(results)

    # Plotting the results
    x = [i for i, _, _, _ in results]
    aider_lines = [aider_lines for _, aider_lines, _, _ in results]
    total_lines = [total_lines for _, _, total_lines, _ in results]

    plt.fill_between(x, aider_lines, label="Aider Lines", color="skyblue", alpha=0.5)
    plt.fill_between(x, total_lines, label="Total Lines", color="lightgreen", alpha=0.5)
    plt.xlabel("Commit Number")
    plt.ylabel("Lines of Code")
    plt.title("Aider Lines and Total Lines Over Time")
    plt.legend()
    plt.savefig("aider_plot.png")
    with open("aider_plot.png", "rb") as f:
        imgcat(f.read())


def main():
    # return history()

    if len(sys.argv) < 2:
        return process_repo()

    fnames = sys.argv[1:]
    process_fnames(fnames, ".")


if __name__ == "__main__":
    main()
