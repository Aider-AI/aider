#!/usr/bin/env python3

import os
import re
from collections import defaultdict
from datetime import datetime

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# GitHub API configuration
GITHUB_API_URL = "https://api.github.com"
REPO_OWNER = "paul-gauthier"
REPO_NAME = "aider"
TOKEN = os.getenv("GITHUB_TOKEN")

headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}


def get_issues(state="open"):
    issues = []
    page = 1
    while True:
        response = requests.get(
            f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/issues",
            headers=headers,
            params={"state": state, "page": page, "per_page": 100},
        )
        response.raise_for_status()
        page_issues = response.json()
        if not page_issues:
            break
        issues.extend(page_issues)
        page += 1
    return issues


def group_issues_by_subject(issues):
    grouped_issues = defaultdict(list)
    pattern = r"Uncaught .+ in .+ line \d+"
    for issue in issues:
        if re.search(pattern, issue["title"]):
            subject = issue["title"]
            grouped_issues[subject].append(issue)
    return grouped_issues


def find_oldest_issue(subject, all_issues):
    oldest_issue = None
    oldest_date = datetime.now()

    for issue in all_issues:
        if issue["title"] == subject:
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

    comment_body = (
        f"This looks like a duplicate of #{oldest_issue['number']}, so I'm going to close it so"
        " discussion can happen there. Please let me know if you think it's actually a distinct"
        " issue."
    )

    # Post comment
    response = requests.post(comment_url, headers=headers, json={"body": comment_body})
    response.raise_for_status()

    # Close issue
    response = requests.patch(close_url, headers=headers, json={"state": "closed"})
    response.raise_for_status()

    print(f"  - Commented and closed issue #{issue['number']}")


def main():
    if not TOKEN:
        print("Error: Missing GITHUB_TOKEN environment variable. Please check your .env file.")
        return

    all_issues = get_issues("all")
    open_issues = [issue for issue in all_issues if issue["state"] == "open"]
    grouped_open_issues = group_issues_by_subject(open_issues)

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

        # Confirmation prompt
        confirm = input("Do you want to comment and close duplicate issues? (y/n): ")
        if confirm.lower() != "y":
            print("Skipping this group of issues.")
            continue

        # Comment and close duplicate issues
        for issue in issues:
            if issue["number"] != oldest_issue["number"]:
                comment_and_close_duplicate(issue, oldest_issue)

        print(f"Oldest issue #{oldest_issue['number']} left open")


if __name__ == "__main__":
    main()
