#!/usr/bin/env python

import argparse
import datetime
import os
import re
import subprocess
import sys

from packaging import version


# Function to check if we are on the main branch
def check_branch():
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    if branch != "main":
        print("Error: Not on the main branch.")
        sys.exit(1)


# Function to check if the working directory is clean
def check_working_directory_clean():
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
    if status:
        print("Error: Working directory is not clean.")
        sys.exit(1)


# Function to fetch the latest changes and check if the main branch is up to date
def check_main_branch_up_to_date():
    subprocess.run(["git", "fetch", "origin"], check=True)
    local_main = subprocess.run(
        ["git", "rev-parse", "main"], capture_output=True, text=True
    ).stdout.strip()
    print(f"Local main commit hash: {local_main}")
    origin_main = subprocess.run(
        ["git", "rev-parse", "origin/main"], capture_output=True, text=True
    ).stdout.strip()
    print(f"Origin main commit hash: {origin_main}")
    if local_main != origin_main:
        local_date = subprocess.run(
            ["git", "show", "-s", "--format=%ci", "main"], capture_output=True, text=True
        ).stdout.strip()
        origin_date = subprocess.run(
            ["git", "show", "-s", "--format=%ci", "origin/main"], capture_output=True, text=True
        ).stdout.strip()
        local_date = datetime.datetime.strptime(local_date, "%Y-%m-%d %H:%M:%S %z")
        origin_date = datetime.datetime.strptime(origin_date, "%Y-%m-%d %H:%M:%S %z")
        if local_date < origin_date:
            print(
                "Error: The local main branch is behind origin/main. Please pull the latest"
                " changes."
            )
        elif local_date > origin_date:
            print(
                "Error: The origin/main branch is behind the local main branch. Please push"
                " your changes."
            )
        else:
            print("Error: The main branch and origin/main have diverged.")
        sys.exit(1)


# Function to check if we can push to the origin repository
def check_ok_to_push():
    print("Checking if it's ok to push to origin repository...")
    result = subprocess.run(["git", "push", "--dry-run", "origin"])

    if result.returncode != 0:
        print("Error: Cannot push to origin repository.")
        sys.exit(1)

    print("Push to origin repository is possible.")


def main():
    parser = argparse.ArgumentParser(description="Bump version")
    parser.add_argument("new_version", help="New version in x.y.z format")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print each step without actually executing them"
    )
    parser.add_argument("--force", action="store_true", help="Skip pre-push checks")

    args = parser.parse_args()
    dry_run = args.dry_run
    force = args.force

    # Perform checks before proceeding unless --force is used
    if not force:
        check_branch()
        check_working_directory_clean()
        check_main_branch_up_to_date()
        check_ok_to_push()
    else:
        print("Skipping pre-push checks due to --force flag.")

    new_version_str = args.new_version
    if not re.match(r"^\d+\.\d+\.\d+$", new_version_str):
        raise ValueError(f"Invalid version format, must be x.y.z: {new_version_str}")

    new_version = version.parse(new_version_str)
    incremented_version = version.Version(
        f"{new_version.major}.{new_version.minor}.{new_version.micro + 1}"
    )

    from aider import __version__ as current_version

    if new_version <= version.parse(current_version):
        raise ValueError(
            f"New version {new_version} must be greater than the current version {current_version}"
        )

    with open("aider/__init__.py", "r") as f:
        content = f.read()
    updated_content = re.sub(r'__version__ = ".+?"', f'__version__ = "{new_version}"', content)

    print("Updating aider/__init__.py with new version:")
    print(updated_content)
    if not dry_run:
        with open("aider/__init__.py", "w") as f:
            f.write(updated_content)

    git_commands = [
        ["git", "add", "aider/__init__.py"],
        ["git", "commit", "-m", f"version bump to {new_version}"],
        ["git", "tag", f"v{new_version}"],
        ["git", "push", "origin", "--no-verify"],
        ["git", "push", "origin", f"v{new_version}", "--no-verify"],
    ]

    for cmd in git_commands:
        print(f"Running: {' '.join(cmd)}")
        if not dry_run:
            subprocess.run(
                cmd,
                check=True,
            )

    new_dev_version = f"{incremented_version}.dev"
    updated_dev_content = re.sub(
        r'__version__ = ".+?"', f'__version__ = "{new_dev_version}"', content
    )

    print()
    print("Updating aider/__init__.py with new dev version:")
    print(updated_dev_content)
    if not dry_run:
        with open("aider/__init__.py", "w") as f:
            f.write(updated_dev_content)

    git_commands_dev = [
        ["git", "add", "aider/__init__.py"],
        ["git", "commit", "-m", f"set version to {new_dev_version}"],
        ["git", "tag", f"v{new_dev_version}"],
        ["git", "push", "origin", "--no-verify"],
        ["git", "push", "origin", f"v{new_dev_version}", "--no-verify"],
    ]

    for cmd in git_commands_dev:
        print(f"Running: {' '.join(cmd)}")
        if not dry_run:
            subprocess.run(cmd, check=True)

    # Remove aider/_version.py if it exists
    version_file = "aider/_version.py"
    if os.path.exists(version_file):
        print(f"Removing {version_file}")
        if not dry_run:
            os.remove(version_file)


if __name__ == "__main__":
    main()
