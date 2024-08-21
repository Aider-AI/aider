#!/usr/bin/env python3

import argparse
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from operator import itemgetter

import semver
import yaml
from tqdm import tqdm


def blame(start_tag, end_tag=None):
    commits = get_all_commit_hashes_between_tags(start_tag, end_tag)
    commits = [commit[:hash_len] for commit in commits]

    authors = get_commit_authors(commits)

    revision = end_tag if end_tag else "HEAD"
    files = run(["git", "ls-tree", "-r", "--name-only", revision]).strip().split("\n")
    files = [
        f
        for f in files
        if f.endswith((".py", ".scm", ".sh", "Dockerfile", "Gemfile"))
        or (f.startswith(".github/workflows/") and f.endswith(".yml"))
    ]
    files = [f for f in files if not f.endswith("prompts.py")]

    all_file_counts = {}
    grand_total = defaultdict(int)
    aider_total = 0
    for file in files:
        file_counts = get_counts_for_file(start_tag, end_tag, authors, file)
        if file_counts:
            all_file_counts[file] = file_counts
            for author, count in file_counts.items():
                grand_total[author] += count
                if "(aider)" in author.lower():
                    aider_total += count

    total_lines = sum(grand_total.values())
    aider_percentage = (aider_total / total_lines) * 100 if total_lines > 0 else 0

    end_date = get_tag_date(end_tag if end_tag else "HEAD")

    return all_file_counts, grand_total, total_lines, aider_total, aider_percentage, end_date


def get_all_commit_hashes_between_tags(start_tag, end_tag=None):
    if end_tag:
        res = run(["git", "rev-list", f"{start_tag}..{end_tag}"])
    else:
        res = run(["git", "rev-list", f"{start_tag}..HEAD"])

    if res:
        commit_hashes = res.strip().split("\n")
        return commit_hashes


def run(cmd):
    # Get all commit hashes since the specified tag
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def get_commit_authors(commits):
    commit_to_author = dict()
    for commit in commits:
        author = run(["git", "show", "-s", "--format=%an", commit]).strip()
        commit_message = run(["git", "show", "-s", "--format=%s", commit]).strip()
        if commit_message.lower().startswith("aider:"):
            author += " (aider)"
        commit_to_author[commit] = author
    return commit_to_author


hash_len = len("44e6fefc2")


def process_all_tags_since(start_tag):
    tags = get_all_tags_since(start_tag)
    # tags += ['HEAD']

    results = []
    for i in tqdm(range(len(tags) - 1), desc="Processing tags"):
        start_tag, end_tag = tags[i], tags[i + 1]
        all_file_counts, grand_total, total_lines, aider_total, aider_percentage, end_date = blame(
            start_tag, end_tag
        )
        results.append(
            {
                "start_tag": start_tag,
                "end_tag": end_tag,
                "end_date": end_date.strftime("%Y-%m-%d"),
                "file_counts": all_file_counts,
                "grand_total": {
                    author: count
                    for author, count in sorted(
                        grand_total.items(), key=itemgetter(1), reverse=True
                    )
                },
                "total_lines": total_lines,
                "aider_total": aider_total,
                "aider_percentage": round(aider_percentage, 2),
            }
        )
    return results


def get_latest_version_tag():
    all_tags = run(["git", "tag", "--sort=-v:refname"]).strip().split("\n")
    for tag in all_tags:
        if semver.Version.is_valid(tag[1:]) and tag.endswith(".0"):
            return tag
    return None


def main():
    parser = argparse.ArgumentParser(description="Get aider/non-aider blame stats")
    parser.add_argument("start_tag", nargs="?", help="The tag to start from (optional)")
    parser.add_argument("--end-tag", help="The tag to end at (default: HEAD)", default=None)
    parser.add_argument(
        "--all-since",
        action="store_true",
        help=(
            "Find all tags since the specified tag and print aider percentage between each pair of"
            " successive tags"
        ),
    )
    parser.add_argument(
        "--output", help="Output file to save the YAML results", type=str, default=None
    )
    args = parser.parse_args()

    if not args.start_tag:
        args.start_tag = get_latest_version_tag()
        if not args.start_tag:
            print("Error: No valid vX.Y.0 tag found.")
            return

    if args.all_since:
        results = process_all_tags_since(args.start_tag)
        yaml_output = yaml.dump(results, sort_keys=True)
    else:
        all_file_counts, grand_total, total_lines, aider_total, aider_percentage, end_date = blame(
            args.start_tag, args.end_tag
        )

        result = {
            "start_tag": args.start_tag,
            "end_tag": args.end_tag or "HEAD",
            "end_date": end_date.strftime("%Y-%m-%d"),
            "file_counts": all_file_counts,
            "grand_total": {
                author: count
                for author, count in sorted(grand_total.items(), key=itemgetter(1), reverse=True)
            },
            "total_lines": total_lines,
            "aider_total": aider_total,
            "aider_percentage": round(aider_percentage, 2),
        }

        yaml_output = yaml.dump(result, sort_keys=True)

    if args.output:
        with open(args.output, "w") as f:
            f.write(yaml_output)
    else:
        print(yaml_output)

    if not args.all_since:
        print(f"- Aider wrote {round(aider_percentage)}% of the code in this release.")


def get_counts_for_file(start_tag, end_tag, authors, fname):
    try:
        if end_tag:
            text = run(["git", "blame", f"{start_tag}..{end_tag}", "--", fname])
        else:
            text = run(["git", "blame", f"{start_tag}..HEAD", "--", fname])
        if not text:
            return None
        text = text.splitlines()
        line_counts = defaultdict(int)
        for line in text:
            if line.startswith("^"):
                continue
            hsh = line[:hash_len]
            author = authors.get(hsh, "Unknown")
            line_counts[author] += 1

        return dict(line_counts)
    except subprocess.CalledProcessError as e:
        if "no such path" in str(e).lower():
            # File doesn't exist in this revision range, which is okay
            return None
        else:
            # Some other error occurred
            print(f"Warning: Unable to blame file {fname}. Error: {e}", file=sys.stderr)
            return None


def get_all_tags_since(start_tag):
    all_tags = run(["git", "tag", "--sort=v:refname"]).strip().split("\n")
    start_version = semver.Version.parse(start_tag[1:])  # Remove 'v' prefix
    filtered_tags = [
        tag
        for tag in all_tags
        if semver.Version.is_valid(tag[1:]) and semver.Version.parse(tag[1:]) >= start_version
    ]
    return [tag for tag in filtered_tags if tag.endswith(".0")]


def get_tag_date(tag):
    date_str = run(["git", "log", "-1", "--format=%ai", tag]).strip()
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")


if __name__ == "__main__":
    main()
