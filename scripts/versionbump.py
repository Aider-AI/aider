import argparse
import re
import subprocess

from packaging import version


def main():
    parser = argparse.ArgumentParser(description="Bump version")
    parser.add_argument("new_version", help="New version in x.y.z format")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print each step without actually executing them"
    )
    args = parser.parse_args()
    dry_run = args.dry_run

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
