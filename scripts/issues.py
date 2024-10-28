#!/usr/bin/env python3

import argparse
import os
import re
from collections import defaultdict
from datetime import datetime

import requests
from dotenv import load_dotenv
from tqdm import tqdm


def has_been_reopened(issue_number):
    timeline_url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue_number}/timeline"
    response = requests.get(timeline_url, headers=headers)
    response.raise_for_status()
    events = response.json()
    return any(event["event"] == "reopened" for event in events if "event" in event)


# Load environment variables from .env file
load_dotenv()

DUPLICATE_COMMENT = """Thanks for trying aider and filing this issue.

This looks like a duplicate of #{oldest_issue_number}. Please see the comments there for more information, and feel free to continue the discussion within that issue.

I'm going to close this issue for now. But please let me know if you think this is actually a distinct issue and I will reopen this issue."""  # noqa

# GitHub API configuration
GITHUB_API_URL = "https://api.github.com"
REPO_OWNER = "Aider-AI"
REPO_NAME = "aider"
TOKEN = os.getenv("GITHUB_TOKEN")

headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}


def get_issues(state="open"):
    issues = []
    page = 1
    per_page = 100

    # First, get the total count of issues
    response = requests.get(
        f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues",
        headers=headers,
        params={"state": state, "per_page": 1},
    )
    response.raise_for_status()
    total_count = int(response.headers.get("Link", "").split("page=")[-1].split(">")[0])
    total_pages = (total_count + per_page - 1) // per_page

    with tqdm(total=total_pages, desc="Collecting issues", unit="page") as pbar:
        while True:
            response = requests.get(
                f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues",
                headers=headers,
                params={"state": state, "page": page, "per_page": per_page},
            )
            response.raise_for_status()
            page_issues = response.json()
            if not page_issues:
                break
            issues.extend(page_issues)
            page += 1
            pbar.update(1)
    return issues


def group_issues_by_subject(issues):
    grouped_issues = defaultdict(list)
    pattern = r"Uncaught .+ in .+ line \d+"
    for issue in issues:
        if re.search(pattern, issue["title"]) and not has_been_reopened(issue["number"]):
            subject = issue["title"]
            grouped_issues[subject].append(issue)
    return grouped_issues


def find_oldest_issue(subject, all_issues):
    oldest_issue = None
    oldest_date = datetime.now()

    for issue in all_issues:
        if issue["title"] == subject and not has_been_reopened(issue["number"]):
            created_at = datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            if created_at < oldest_date:
                oldest_date = created_at
                oldest_issue = issue

    return oldest_issue


def comment_and_close_duplicate(issue, oldest_issue):
    comment_url = (
        f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue['number']}/comments"
    )
    close_url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues/{issue['number']}"

    comment_body = DUPLICATE_COMMENT.format(oldest_issue_number=oldest_issue["number"])

    # Post comment
    response = requests.post(comment_url, headers=headers, json={"body": comment_body})
    response.raise_for_status()

    # Close issue
    response = requests.patch(close_url, headers=headers, json={"state": "closed"})
    response.raise_for_status()

    print(f"  - Commented and closed issue #{issue['number']}")


def main():
    parser = argparse.ArgumentParser(description="Handle duplicate GitHub issues")
    parser.add_argument(
        "--yes", action="store_true", help="Automatically close duplicates without prompting"
    )
    args = parser.parse_args()

    if not TOKEN:
        print("Error: Missing GITHUB_TOKEN environment variable. Please check your .env file.")
        return

    all_issues = get_issues("all")
    open_issues = [issue for issue in all_issues if issue["state"] == "open"]
    grouped_open_issues = group_issues_by_subject(open_issues)

    print("Analyzing issues (skipping reopened issues)...")
    for subject, issues in grouped_open_issues.items():
        oldest_issue = find_oldest_issue(subject, all_issues)
        if not oldest_issue:
            continue

        related_issues = set(issue["number"] for issue in issues)
        related_issues.add(oldest_issue["number"])
        if len(related_issues) <= 1:
            continue

        print(f"\nIssue: {subject}")
        print(f"Open issues: {len(issues)}")
        sorted_issues = sorted(issues, key=lambda x: x["number"], reverse=True)
        for issue in sorted_issues:
            print(f"  - #{issue['number']}: {issue['comments']} comments {issue['html_url']}")

        print(
            f"Oldest issue: #{oldest_issue['number']}: {oldest_issue['comments']} comments"
            f" {oldest_issue['html_url']} ({oldest_issue['state']})"
        )

        if not args.yes:
            # Confirmation prompt
            confirm = input("Do you want to comment and close duplicate issues? (y/n): ")
            if confirm.lower() != "y":
                print("Skipping this group of issues.")
                continue

        # Comment and close duplicate issues
        for issue in issues:
            if issue["number"] != oldest_issue["number"]:
                comment_and_close_duplicate(issue, oldest_issue)

        if oldest_issue["state"] == "open":
            print(f"Oldest issue #{oldest_issue['number']} left open")


if __name__ == "__main__":
    main()
