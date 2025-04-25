#!/usr/bin/env python3

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests
import yaml
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account

TOKENS_PER_WEEK = "15B"

# Badge tooltip texts
GITHUB_STARS_TOOLTIP = "Total number of GitHub stars the Aider project has received"
PYPI_DOWNLOADS_TOOLTIP = "Total number of installations via pip from PyPI"
TOKENS_WEEKLY_TOOLTIP = "Number of tokens processed weekly by Aider users"
OPENROUTER_TOOLTIP = "Aider's ranking among applications on the OpenRouter platform"
SINGULARITY_TOOLTIP = "Percentage of the new code in Aider's last release written by Aider itself"

# Cache settings
CACHE_DIR = os.path.expanduser("~/.cache/aider-badges")
CACHE_DURATION = 24 * 60 * 60  # 24 hours in seconds


def ensure_cache_dir():
    """Create the cache directory if it doesn't exist"""
    os.makedirs(CACHE_DIR, exist_ok=True)


def get_cache_path(package_name):
    """Get the path to the cache file for a package"""
    return os.path.join(CACHE_DIR, f"{package_name}_downloads.json")


def read_from_cache(package_name):
    """
    Read download statistics from cache if available and not expired
    Returns (downloads, is_valid) tuple where is_valid is True if cache is valid
    """
    cache_path = get_cache_path(package_name)

    if not os.path.exists(cache_path):
        return None, False

    try:
        with open(cache_path, "r") as f:
            cache_data = json.load(f)

        # Check if cache is expired
        timestamp = cache_data.get("timestamp", 0)
        current_time = time.time()

        if current_time - timestamp > CACHE_DURATION:
            return None, False

        return cache_data.get("downloads"), True
    except Exception as e:
        print(f"Error reading from cache: {e}", file=sys.stderr)
        return None, False


def write_to_cache(package_name, downloads):
    """Write download statistics to cache"""
    cache_path = get_cache_path(package_name)

    try:
        ensure_cache_dir()
        cache_data = {
            "downloads": downloads,
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        return True
    except Exception as e:
        print(f"Error writing to cache: {e}", file=sys.stderr)
        return False


def get_downloads_from_bigquery(credentials_path=None, package_name="aider-chat"):
    """
    Fetch download statistics for a package from Google BigQuery PyPI dataset
    Uses a 24-hour cache to avoid unnecessary API calls
    """
    # Check if we have a valid cached value
    cached_downloads, is_valid = read_from_cache(package_name)
    if is_valid:
        print(f"Using cached download statistics for {package_name} (valid for 24 hours)")
        return cached_downloads

    print(f"Cache invalid or expired, fetching fresh download statistics for {package_name}")

    try:
        # Initialize credentials if path provided
        credentials = None
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )

        # Create a client
        client = bigquery.Client(credentials=credentials)

        # Query to get total downloads for the package, excluding CI/CD systems
        query = f"""
            SELECT COUNT(*) as total_downloads
            FROM `bigquery-public-data.pypi.file_downloads`
            WHERE file.project = '{package_name}'
            AND NOT (
                -- Exclude common CI/CD systems based on installer name patterns
                LOWER(details.installer.name) LIKE '%github%' OR
                LOWER(details.installer.name) LIKE '%travis%' OR
                LOWER(details.installer.name) LIKE '%circle%' OR
                LOWER(details.installer.name) LIKE '%jenkins%' OR
                LOWER(details.installer.name) LIKE '%gitlab%' OR
                LOWER(details.installer.name) LIKE '%azure%' OR
                LOWER(details.installer.name) LIKE '%ci%' OR
                LOWER(details.installer.name) LIKE '%cd%' OR
                LOWER(details.installer.name) LIKE '%bot%' OR
                LOWER(details.installer.name) LIKE '%build%'
            )
        """

        # Execute the query
        query_job = client.query(query)
        results = query_job.result()

        # Get the first (and only) row
        for row in results:
            downloads = row.total_downloads
            # Write the result to cache
            write_to_cache(package_name, downloads)
            return downloads

        return 0
    except Exception as e:
        print(f"Error fetching download statistics from BigQuery: {e}", file=sys.stderr)
        # If there was an error but we have a cached value, use it even if expired
        if cached_downloads is not None:
            print("Using expired cached data due to BigQuery error")
            return cached_downloads
        return None


def get_total_downloads(
    api_key=None, package_name="aider-chat", use_bigquery=False, credentials_path=None
):
    """
    Fetch total downloads for a Python package

    If use_bigquery is True, fetches from BigQuery.
    Otherwise uses pepy.tech API (requires api_key).
    """
    if use_bigquery:
        print(f"Using BigQuery to fetch download statistics for {package_name}")
        return get_downloads_from_bigquery(credentials_path, package_name)

    # Fall back to pepy.tech API
    print(f"Using pepy.tech API to fetch download statistics for {package_name}")
    if not api_key:
        print("API key not provided for pepy.tech", file=sys.stderr)
        sys.exit(1)

    url = f"https://api.pepy.tech/api/v2/projects/{package_name}"
    headers = {"X-API-Key": api_key}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()
        total_downloads = data.get("total_downloads", 0)

        return total_downloads
    except requests.exceptions.RequestException as e:
        print(f"Error fetching download statistics from pepy.tech: {e}", file=sys.stderr)
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
        return f"{number / 1_000_000_000:.1f}B"
    elif number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.1f}K"
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

    markdown = f"""  <a href="https://github.com/Aider-AI/aider/stargazers"><img alt="GitHub Stars" title="{GITHUB_STARS_TOOLTIP}"
src="https://img.shields.io/github/stars/Aider-AI/aider?style=flat-square&logo=github&color=f1c40f&labelColor=555555"/></a>
  <a href="https://pypi.org/project/aider-chat/"><img alt="PyPI Downloads" title="{PYPI_DOWNLOADS_TOOLTIP}"
src="https://img.shields.io/badge/📦%20Installs-{downloads_formatted}-2ecc71?style=flat-square&labelColor=555555"/></a>
  <img alt="Tokens per week" title="{TOKENS_WEEKLY_TOOLTIP}"
src="https://img.shields.io/badge/📈%20Tokens%2Fweek-{TOKENS_PER_WEEK}-3498db?style=flat-square&labelColor=555555"/>
  <a href="https://openrouter.ai/#options-menu"><img alt="OpenRouter Ranking" title="{OPENROUTER_TOOLTIP}"
src="https://img.shields.io/badge/🏆%20OpenRouter-Top%2020-9b59b6?style=flat-square&labelColor=555555"/></a>
  <a href="https://aider.chat/HISTORY.html"><img alt="Singularity" title="{SINGULARITY_TOOLTIP}"
src="https://img.shields.io/badge/🔄%20Singularity-{aider_percent_rounded}%25-e74c3c?style=flat-square&labelColor=555555"/></a>"""  # noqa

    return markdown


def get_badges_md():
    """
    Get all statistics and return the generated badges markdown
    """
    # Load environment variables from .env file
    load_dotenv()

    # Check if we should use BigQuery and get credentials path
    bigquery_env = os.environ.get("USE_BIGQUERY", "false")
    use_bigquery = bigquery_env.lower() in ("true", "1", "yes") or os.path.exists(bigquery_env)
    credentials_path = bigquery_env if os.path.exists(bigquery_env) else None

    # Get API key from environment variable if not using BigQuery
    api_key = None
    if not use_bigquery:
        api_key = os.environ.get("PEPY_API_KEY")
        if not api_key:
            print(
                (
                    "API key not provided and BigQuery not enabled. Please set PEPY_API_KEY"
                    " environment variable"
                ),
                file=sys.stderr,
            )
            sys.exit(1)

    # Get PyPI downloads for the default package
    total_downloads = get_total_downloads(api_key, "aider-chat", use_bigquery, credentials_path)

    # Get GitHub stars for the default repo
    stars = get_github_stars("paul-gauthier/aider")

    # Get Aider contribution percentage in latest release
    percentage, _ = get_latest_release_aider_percentage()

    # Generate and return badges markdown
    return generate_badges_md(total_downloads, stars, percentage)


def get_badges_html():
    """
    Get all statistics and return HTML-formatted badges
    """
    # Load environment variables from .env file
    load_dotenv()

    # Check if we should use BigQuery and get credentials path
    bigquery_env = os.environ.get("USE_BIGQUERY", "false")
    use_bigquery = bigquery_env.lower() in ("true", "1", "yes") or os.path.exists(bigquery_env)
    credentials_path = bigquery_env if os.path.exists(bigquery_env) else None

    # Get API key from environment variable if not using BigQuery
    api_key = None
    if not use_bigquery:
        api_key = os.environ.get("PEPY_API_KEY")
        if not api_key:
            print(
                (
                    "API key not provided and BigQuery not enabled. Please set PEPY_API_KEY"
                    " environment variable"
                ),
                file=sys.stderr,
            )
            sys.exit(1)

    # Get PyPI downloads for the default package
    total_downloads = get_total_downloads(api_key, "aider-chat", use_bigquery, credentials_path)

    # Get GitHub stars for the default repo
    stars = get_github_stars("paul-gauthier/aider")

    # Get Aider contribution percentage in latest release
    percentage, _ = get_latest_release_aider_percentage()

    # Format values
    downloads_formatted = format_number(total_downloads)
    # Stars should be rounded to whole numbers
    if stars is None:
        stars_formatted = "0"
    elif stars >= 1_000_000_000:
        stars_formatted = f"{round(stars / 1_000_000_000)}B"
    elif stars >= 1_000_000:
        stars_formatted = f"{round(stars / 1_000_000)}M"
    elif stars >= 1_000:
        stars_formatted = f"{round(stars / 1_000)}K"
    else:
        stars_formatted = str(int(round(stars)))
    aider_percent_rounded = round(percentage)

    # Generate HTML badges
    html = f"""<a href="https://github.com/Aider-AI/aider" class="github-badge badge-stars" title="{GITHUB_STARS_TOOLTIP}">
    <span class="badge-label">⭐ GitHub Stars</span>
    <span class="badge-value">{stars_formatted}</span>
</a>
<a href="https://pypi.org/project/aider-chat/" class="github-badge badge-installs" title="{PYPI_DOWNLOADS_TOOLTIP}">
    <span class="badge-label">📦 Installs</span>
    <span class="badge-value">{downloads_formatted}</span>
</a>
<div class="github-badge badge-tokens" title="{TOKENS_WEEKLY_TOOLTIP}">
    <span class="badge-label">📈 Tokens/week</span>
    <span class="badge-value">{TOKENS_PER_WEEK}</span>
</div>
<a href="https://openrouter.ai/#options-menu" class="github-badge badge-router" title="{OPENROUTER_TOOLTIP}">
    <span class="badge-label">🏆 OpenRouter</span>
    <span class="badge-value">Top 20</span>
</a>
<a href="/HISTORY.html" class="github-badge badge-coded" title="{SINGULARITY_TOOLTIP}">
    <span class="badge-label">🔄 Singularity</span>
    <span class="badge-value">{aider_percent_rounded}%</span>
</a>"""  # noqa

    return html


def get_testimonials_js():
    """
    Extract testimonials from README.md and format them as JavaScript array
    """
    # Path to README.md, relative to this script
    readme_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md"
    )

    testimonials = []
    in_testimonials_section = False

    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

            # Find the testimonials section
            for i, line in enumerate(lines):
                if line.strip() == "## Kind Words From Users":
                    in_testimonials_section = True
                    # Start processing from the next line
                    start_idx = i + 1
                    break

            # If we found the section
            if in_testimonials_section:
                for i in range(start_idx, len(lines)):
                    line = lines[i]
                    # If we've hit another section, stop
                    if line.startswith("##"):
                        break

                    # Process testimonial lines
                    if line.strip().startswith('- *"'):
                        try:
                            # Get the full line
                            full_line = line.strip()

                            # Extract the quote text between *" and "*
                            if '*"' in full_line and '"*' in full_line:
                                quote_parts = full_line.split('*"')
                                if len(quote_parts) > 1:
                                    quote_text = quote_parts[1].split('"*')[0].strip()

                                    # Default values
                                    author = "Anonymous"
                                    link = ""

                                    # Try to extract author and link if they exist
                                    # Check for the em dash format first: "— [author](link)"
                                    if "— [" in full_line and "](" in full_line:
                                        author_parts = full_line.split("— [")
                                        if len(author_parts) > 1:
                                            author = author_parts[1].split("]")[0].strip()

                                            # Extract the link if it exists
                                            link_parts = full_line.split("](")
                                            if len(link_parts) > 1:
                                                link = link_parts[1].split(")")[0].strip()
                                    # Check for regular dash format: "- [author](link)"
                                    elif " - [" in full_line and "](" in full_line:
                                        author_parts = full_line.split(" - [")
                                        if len(author_parts) > 1:
                                            author = author_parts[1].split("]")[0].strip()

                                            # Extract the link if it exists
                                            link_parts = full_line.split("](")
                                            if len(link_parts) > 1:
                                                link = link_parts[1].split(")")[0].strip()
                                    # Check for em dash without link: "— author"
                                    elif "— " in full_line:
                                        # Format without a link, just plain text author
                                        author_parts = full_line.split("— ")
                                        if len(author_parts) > 1:
                                            author = author_parts[1].strip()
                                    # Check for regular dash without link: "- author"
                                    elif " - " in full_line:
                                        # Format without a link, just plain text author
                                        author_parts = full_line.split(" - ")
                                        if len(author_parts) > 1:
                                            author = author_parts[1].strip()

                                    testimonials.append(
                                        {"text": quote_text, "author": author, "link": link}
                                    )
                        except Exception as e:
                            print(
                                f"Error parsing testimonial line: {line}. Error: {e}",
                                file=sys.stderr,
                            )
                            continue

        # Format as JavaScript array with script tags
        if not testimonials:
            print("No testimonials found in README.md", file=sys.stderr)
            return "<script>\nconst testimonials = [];\n</script>"

        js_array = "<script>\nconst testimonials = [\n"
        for i, t in enumerate(testimonials):
            js_array += "    {\n"
            js_array += f"        text: \"{t['text']}\",\n"
            js_array += f"        author: \"{t['author']}\",\n"
            js_array += f"        link: \"{t['link']}\"\n"
            js_array += "    }"
            if i < len(testimonials) - 1:
                js_array += ","
            js_array += "\n"
        js_array += "];\n</script>"

        return js_array

    except Exception as e:
        print(f"Error reading testimonials from README: {e}", file=sys.stderr)
        # Return empty array as fallback
        return "<script>\nconst testimonials = [];\n</script>"


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Ensure cache directory exists
    ensure_cache_dir()

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
    parser.add_argument(
        "--use-bigquery",
        action="store_true",
        help="Use BigQuery to fetch download statistics instead of pepy.tech",
    )
    parser.add_argument(
        "--credentials-path", help="Path to Google Cloud service account credentials JSON file"
    )
    args = parser.parse_args()

    # Determine whether to use BigQuery and get credentials path
    bigquery_env = os.environ.get("USE_BIGQUERY", "false")
    use_bigquery = (
        args.use_bigquery
        or bigquery_env.lower() in ("true", "1", "yes")
        or os.path.exists(bigquery_env)
    )
    credentials_path = args.credentials_path or (
        bigquery_env if os.path.exists(bigquery_env) else None
    )

    # Check for required parameters
    api_key = None
    if not use_bigquery:
        # Get API key from args or environment variable
        api_key = args.api_key or os.environ.get("PEPY_API_KEY")
        if not api_key:
            print(
                (
                    "API key not provided and BigQuery not enabled. Please set PEPY_API_KEY"
                    " environment variable, use --api-key, or enable BigQuery with --use-bigquery"
                ),
                file=sys.stderr,
            )
            sys.exit(1)
    elif use_bigquery and not credentials_path and not args.credentials_path:
        print(
            (
                "BigQuery enabled but no credentials provided. Please set"
                " USE_BIGQUERY to path of credentials file or use --credentials-path"
            ),
            file=sys.stderr,
        )
        # Continue execution - BigQuery might work without explicit credentials in some environments

    # Get PyPI downloads
    total_downloads = get_total_downloads(api_key, args.package, use_bigquery, credentials_path)
    print(f"Total downloads for {args.package}: {total_downloads:,}")

    # Get GitHub stars
    stars = get_github_stars(args.github_repo)
    if stars is not None:
        print(f"GitHub stars for {args.github_repo}: {stars:,}")

    # Get Aider contribution percentage in latest release
    percentage, version = get_latest_release_aider_percentage()
    print(f"Aider wrote {percentage:.2f}% of code in the LATEST release ({version})")

    # Get testimonials JavaScript
    testimonials_js = get_testimonials_js()
    print("\nTestimonials JavaScript:")
    print(testimonials_js)


if __name__ == "__main__":
    main()
