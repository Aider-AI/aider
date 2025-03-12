#!/usr/bin/env python3

import json
import os
import sys
import time

import requests


def get_default_branch(owner, repo):
    """Get the default branch of a GitHub repository using the API."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json().get("default_branch")
    except requests.exceptions.RequestException:
        return None


def try_download_tags(owner, repo, branch, directory, output_path):
    """Try to download tags.scm from a specific branch."""
    base_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    if directory:
        tags_url = f"{base_url}/{directory}/queries/tags.scm"
    else:
        tags_url = f"{base_url}/queries/tags.scm"

    try:
        response = requests.get(tags_url)
        response.raise_for_status()

        # Save the file
        with open(output_path, "w") as f:
            f.write(response.text)
        return True
    except requests.exceptions.RequestException:
        return False


def main():
    # Path to the language definitions file
    lang_def_path = "../../tmp/tree-sitter-language-pack/sources/language_definitions.json"

    # Path to store the tags.scm files
    output_dir = "aider/queries/tree-sitter-language-pack"

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Common branch names to try if API fails and config branch doesn't work
    common_branches = ["main", "master", "dev", "develop"]

    try:
        # Load the language definitions
        with open(lang_def_path, "r") as f:
            lang_defs = json.load(f)
    except Exception as e:
        print(f"Error loading language definitions: {e}")
        sys.exit(1)

    print(f"Found {len(lang_defs)} language definitions")

    # Process each language
    successes = 0
    total = len(lang_defs)

    for lang, config in lang_defs.items():
        # Extract repo URL from the config
        repo_url = config.get("repo")
        print(f"Processing {lang} ({repo_url})...")

        if not repo_url:
            print(f"Skipping {lang}: No repository URL found")
            continue

        directory = config.get("directory", "")

        # Parse the GitHub repository URL
        if "github.com" not in repo_url:
            print(f"Skipping {lang}: Not a GitHub repository")
            continue

        # Extract the owner and repo name from the URL
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 5:
            print(f"Skipping {lang}: Invalid GitHub URL format")
            continue

        owner = parts[-2]
        repo = parts[-1]

        # Create output directory and set output file path
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{lang}-tags.scm")

        # Skip if file already exists
        if os.path.exists(output_file):
            print(f"Skipping {lang}: tags.scm already exists")
            successes += 1
            continue

        # Try branches in this order:
        # 1. Branch specified in the config
        # 2. Default branch from GitHub API
        # 3. Common branch names (main, master, etc.)

        branches_to_try = []

        # 1. Branch from config (if specified)
        config_branch = config.get("branch")
        if config_branch:
            branches_to_try.append(config_branch)

        # 2. Default branch from GitHub API
        default_branch = get_default_branch(owner, repo)
        if default_branch and default_branch not in branches_to_try:
            branches_to_try.append(default_branch)

        # 3. Add common branch names
        for branch in common_branches:
            if branch not in branches_to_try:
                branches_to_try.append(branch)

        # Try each branch
        success = False
        for branch in branches_to_try:
            if try_download_tags(owner, repo, branch, directory, output_file):
                print(f"Successfully downloaded tags for {lang} (branch: {branch})")
                success = True
                successes += 1
                break

        if not success:
            print(f"Failed to download tags for {lang} after trying all branches")

        # Be nice to GitHub's API
        time.sleep(0.1)

    print(f"All language tags processed. Downloaded {successes}/{total} successfully.")


if __name__ == "__main__":
    main()
