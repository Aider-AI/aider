#!/usr/bin/env python3

import argparse
import os
import sys

import requests
import yaml
from dotenv import load_dotenv


def get_total_downloads(api_key, package_name="aider-chat"):
    """
    Fetch total downloads for a Python package from pepy.tech API
    """
    url = f"https://api.pepy.tech/api/v2/projects/{package_name}"
    headers = {"X-API-Key": api_key}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()
        total_downloads = data.get("total_downloads", 0)

        return total_downloads
    except requests.exceptions.RequestException as e:
        print(f"Error fetching download statistics: {e}", file=sys.stderr)
        sys.exit(1)


def get_github_stars(repo="paul-gauthier/aider"):
    """
    Fetch the number of GitHub stars for a repository
    """
    url = f"https://api.github.com/repos/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()
        stars = data.get("stargazers_count", 0)

        return stars
    except requests.exceptions.RequestException as e:
        print(f"Error fetching GitHub stars: {e}", file=sys.stderr)
        return None


def get_latest_release_aider_percentage():
    """
    Get the percentage of code written by Aider in the LATEST release
    from the blame.yml file
    """
    blame_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "aider",
        "website",
        "_data",
        "blame.yml",
    )

    try:
        with open(blame_path, "r") as f:
            blame_data = yaml.safe_load(f)

        if not blame_data or len(blame_data) == 0:
            return 0, "unknown"
        
        # Find the latest release by parsing version numbers
        latest_version = None
        latest_release = None
        
        for release in blame_data:
            version_tag = release.get("end_tag", "")
            if not version_tag.startswith("v"):
                continue
                
            # Parse version like "v0.77.0" into a tuple (0, 77, 0)
            try:
                version_parts = tuple(int(part) for part in version_tag[1:].split("."))
                if latest_version is None or version_parts > latest_version:
                    latest_version = version_parts
                    latest_release = release
            except ValueError:
                # Skip if version can't be parsed as integers
                continue
        
        if latest_release:
            percentage = latest_release.get("aider_percentage", 0)
            version = latest_release.get("end_tag", "unknown")
            return percentage, version

        return 0, "unknown"
    except Exception as e:
        print(f"Error reading blame data: {e}", file=sys.stderr)
        return 0, "unknown"


def main():
    # Load environment variables from .env file
    load_dotenv()

    parser = argparse.ArgumentParser(description="Get total downloads and GitHub stars for aider")
    parser.add_argument(
        "--api-key",
        help=(
            "pepy.tech API key (can also be set via PEPY_API_KEY in .env file or environment"
            " variable)"
        ),
    )
    parser.add_argument(
        "--package", default="aider-chat", help="Package name (default: aider-chat)"
    )
    parser.add_argument(
        "--github-repo",
        default="paul-gauthier/aider",
        help="GitHub repository (default: paul-gauthier/aider)",
    )
    args = parser.parse_args()

    # Get API key from args or environment variable (which may be loaded from .env)
    api_key = args.api_key or os.environ.get("PEPY_API_KEY")
    if not api_key:
        print(
            "API key not provided. Please set PEPY_API_KEY environment variable or use --api-key",
            file=sys.stderr,
        )
        sys.exit(1)

    # Get PyPI downloads
    total_downloads = get_total_downloads(api_key, args.package)
    print(f"Total downloads for {args.package}: {total_downloads:,}")

    # Get GitHub stars
    stars = get_github_stars(args.github_repo)
    if stars is not None:
        print(f"GitHub stars for {args.github_repo}: {stars:,}")

    # Get Aider contribution percentage in latest release
    percentage, version = get_latest_release_aider_percentage()
    print(f"Aider wrote {percentage:.2f}% of code in the LATEST release ({version})")


if __name__ == "__main__":
    main()
