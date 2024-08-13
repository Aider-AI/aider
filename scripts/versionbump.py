#!/usr/bin/env python

import argparse
import datetime
import re
import subprocess
import sys

from packaging import version


def check_cog_pyproject():
    result = subprocess.run(["cog", "--check", "pyproject.toml"], capture_output=True, text=True)

    if result.returncode != 0:
        print("Error: cog --check pyproject.toml failed, updating.")
        subprocess.run(["cog", "-r", "pyproject.toml"])
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Bump version")
    parser.add_argument("new_version", help="New version in x.y.z format")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print each step without actually executing them"
    )

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
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        ).stdout
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

    args = parser.parse_args()
    dry_run = args.dry_run

    # Perform checks before proceeding
    check_cog_pyproject()
    check_branch()
    check_working_directory_clean()
    check_main_branch_up_to_date()

    new_version_str = args.new_version
    if not re.match(r"^\d+\.\d+\.\d+$", new_version_str):
        raise ValueError(f"Invalid version format, must be x.y.z: {new_version_str}")

    new_version = version.parse(new_version_str)
    incremented_version = version.Version(
        f"{new_version.major}.{new_version.minor}.{new_version.micro + 1}"
    )

    with open("aider/__init__.py", "r") as f:
        content = f.read()

    current_version = re.search(r'__version__ = "(.+?)"', content).group(1)
    if new_version <= version.parse(current_version):
        raise ValueError(
            f"New version {new_version} must be greater than the current version {current_version}"
        )

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
        ["git", "push", "origin"],
        ["git", "push", "origin", f"v{new_version}"],
    ]

    for cmd in git_commands:
        print(f"Running: {' '.join(cmd)}")
        if not dry_run:
            subprocess.run(cmd, check=True)

    updated_dev_content = re.sub(
        r'__version__ = ".+?"', f'__version__ = "{incremented_version}-dev"', content
    )

    print()
    print("Updating aider/__init__.py with new dev version:")
    print(updated_dev_content)
    if not dry_run:
        with open("aider/__init__.py", "w") as f:
            f.write(updated_dev_content)

    git_commands_dev = [
        ["git", "add", "aider/__init__.py"],
        ["git", "commit", "-m", f"set version to {incremented_version}-dev"],
        ["git", "push", "origin"],
    ]

    for cmd in git_commands_dev:
        print(f"Running: {' '.join(cmd)}")
        if not dry_run:
            subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
