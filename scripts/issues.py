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


def main():
    if not TOKEN:
        print("Error: Missing GITHUB_TOKEN environment variable. Please check your .env file.")
        return

    all_issues = get_issues("all")
    open_issues = [issue for issue in all_issues if issue["state"] == "open"]
    grouped_open_issues = group_issues_by_subject(open_issues)

    for subject, issues in grouped_open_issues.items():
        print(f"\nIssue: {subject}")
        print(f"Open issues: {len(issues)}")
        for issue in issues:
            print(f"  - #{issue['number']}")

        oldest_issue = find_oldest_issue(subject, all_issues)
        if oldest_issue:
            print(
                f"Oldest issue: #{oldest_issue['number']} (created on {oldest_issue['created_at']})"
            )
        else:
            print("No oldest issue found")


if __name__ == "__main__":
    main()
