#!/usr/bin/env python3

import argparse
import json
import os
import sys

import requests


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


def main():
    parser = argparse.ArgumentParser(
        description="Get total downloads for a Python package from pepy.tech"
    )
    parser.add_argument(
        "--api-key", help="pepy.tech API key (or set PEPY_API_KEY environment variable)"
    )
    parser.add_argument(
        "--package", default="aider-chat", help="Package name (default: aider-chat)"
    )
    args = parser.parse_args()

    # Get API key from args or environment variable
    api_key = args.api_key or os.environ.get("PEPY_API_KEY")
    if not api_key:
        print(
            "API key not provided. Please set PEPY_API_KEY environment variable or use --api-key",
            file=sys.stderr,
        )
        sys.exit(1)

    total_downloads = get_total_downloads(api_key, args.package)
    print(f"Total downloads for {args.package}: {total_downloads:,}")


if __name__ == "__main__":
    main()
