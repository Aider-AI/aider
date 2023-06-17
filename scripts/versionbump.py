import argparse
import os
import re
import subprocess
from packaging import version

def main():
    parser = argparse.ArgumentParser(description="Bump version")
    parser.add_argument("new_version", help="New version in x.y.z format")
    args = parser.parse_args()

    new_version = version.parse(args.new_version)
    if not isinstance(new_version, version.Version):
        raise ValueError("Invalid version format")

    with open("aider/__init__.py", "r") as f:
        content = f.read()

    current_version = re.search(r'__version__ = "(.+?)"', content).group(1)
    if new_version <= version.parse(current_version):
        raise ValueError("New version must be greater than the current version")

    updated_content = re.sub(r'__version__ = ".+?"', f'__version__ = "{new_version}"', content)

    with open("aider/__init__.py", "w") as f:
        f.write(updated_content)

    subprocess.run(["git", "add", "aider/__init__.py"])
    subprocess.run(["git", "commit", "-m", f"version bump to {new_version}"])
    subprocess.run(["git", "tag", f"v{new_version}"])
    subprocess.run(["git", "push", "origin"])
    subprocess.run(["git", "push", "origin", f"v{new_version}"])

if __name__ == "__main__":
    main()
