#!/usr/bin/env python3

import json
import os
import sys

import requests


def main():
    # Path to the language definitions file
    lang_def_path = "../../tmp/tree-sitter-language-pack/sources/language_definitions.json"

    # Path to store the tags.scm files
    output_dir = os.path.expanduser("~/tmp/tsl-pack")

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Load the language definitions
        with open(lang_def_path, "r") as f:
            lang_defs = json.load(f)
    except Exception as e:
        print(f"Error loading language definitions: {e}")
        sys.exit(1)

    print(f"Found {len(lang_defs)} language definitions")

    # Process each language
    for lang, config in lang_defs.items():
        print(f"Processing {lang}...")

        # Extract repo URL and branch from the config
        repo_url = config.get("repo")
        if not repo_url:
            print(f"Skipping {lang}: No repository URL found")
            continue

        branch = config.get("branch", "master")
        directory = config.get("directory", "")

        # Parse the GitHub repository URL
        if "github.com" not in repo_url:
            print(f"Skipping {lang}: Not a GitHub repository")
            continue

        # Extract the owner and repo name from the URL
        _, _, _, owner, repo = repo_url.rstrip("/").split("/")

        # Construct the raw file URL
        # Build the GitHub raw content path
        base_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
        if directory:
            tags_url = f"{base_url}/{directory}/queries/tags.scm"
        else:
            tags_url = f"{base_url}/queries/tags.scm"

        # Create the language directory in the output path
        lang_dir = os.path.join(output_dir, lang)
        os.makedirs(os.path.join(lang_dir, "queries"), exist_ok=True)

        # Fetch the tags.scm file
        try:
            response = requests.get(tags_url)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Save the file
            output_file = os.path.join(lang_dir, "queries", "tags.scm")
            with open(output_file, "w") as f:
                f.write(response.text)

            print(f"Successfully downloaded tags for {lang}")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching tags for {lang}: {e}")

    print("All language tags processed")


if __name__ == "__main__":
    main()
