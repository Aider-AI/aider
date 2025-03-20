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


def format_number(number):
    """
    Format a large number with K, M, B suffixes with 1 decimal place
    """
    if number is None:
        return "0"

    if number >= 1_000_000_000:
        return f"{number/1_000_000_000:.1f}B"
    elif number >= 1_000_000:
        return f"{number/1_000_000:.1f}M"
    elif number >= 1_000:
        return f"{number/1_000:.1f}K"
    else:
        return str(number)


def generate_badges_md(downloads, stars, aider_percentage):
    """
    Generate markdown for badges with updated values
    """
    # Format downloads to 1 decimal place with M suffix
    downloads_formatted = format_number(downloads)

    # Round aider percentage to whole number
    aider_percent_rounded = round(aider_percentage)

    markdown = f"""  <a href="https://github.com/Aider-AI/aider/stargazers"><img alt="GitHub Stars" title="Total number of GitHub stars the Aider project has received"
src="https://img.shields.io/github/stars/Aider-AI/aider?style=flat-square&logo=github&color=f1c40f&labelColor=555555"/></a>
  <a href="https://pypi.org/project/aider-chat/"><img alt="PyPI Downloads" title="Total number of installations via pip from PyPI"
src="https://img.shields.io/badge/📦%20Installs-{downloads_formatted}-2ecc71?style=flat-square&labelColor=555555"/></a>
  <img alt="Tokens per week" title="Number of tokens processed weekly by Aider users"
src="https://img.shields.io/badge/📈%20Tokens%2Fweek-15B-e74c3c?style=flat-square&labelColor=555555"/>
  <a href="https://openrouter.ai/"><img alt="OpenRouter Ranking" title="Aider's ranking among applications on the OpenRouter platform"
src="https://img.shields.io/badge/🏆%20OpenRouter-Top%2020-9b59b6?style=flat-square&labelColor=555555"/></a>
  <a href="https://aider.chat/HISTORY.html"><img alt="Singularity" title="Percentage of the new code in Aider's last release written by Aider itself"
src="https://img.shields.io/badge/🔄%20Singularity-{aider_percent_rounded}%25-3498db?style=flat-square&labelColor=555555"/></a>""" # noqa

    return markdown


def get_badges_md():
    """
    Get all statistics and return the generated badges markdown
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.environ.get("PEPY_API_KEY")
    if not api_key:
        print(
            "API key not provided. Please set PEPY_API_KEY environment variable",
            file=sys.stderr,
        )
        sys.exit(1)
    
    # Get PyPI downloads for the default package
    total_downloads = get_total_downloads(api_key, "aider-chat")
    
    # Get GitHub stars for the default repo
    stars = get_github_stars("paul-gauthier/aider")
    
    # Get Aider contribution percentage in latest release
    percentage, _ = get_latest_release_aider_percentage()
    
    # Generate and return badges markdown
    return generate_badges_md(total_downloads, stars, percentage)


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
    parser.add_argument("--markdown", action="store_true", help="Generate markdown badges block")
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

    # Generate and print badges markdown
    badges_md = generate_badges_md(total_downloads, stars, percentage)
    print("\nBadges markdown:\n")
    print(badges_md)


if __name__ == "__main__":
    main()
