#!/usr/bin/env python3

import os
import re
import subprocess
import tempfile

from aider import __version__


def get_base_version():
    # Parse current version like "0.64.2.dev" to get major.minor
    match = re.match(r"(\d+\.\d+)", __version__)
    if not match:
        raise ValueError(f"Could not parse version: {__version__}")
    return match.group(1) + ".0"


def run_git_log():
    base_ver = get_base_version()
    cmd = [
        "git",
        "log",
        "-p",
        f"v{base_ver}..HEAD",
        "--",
        "aider/",
        ":!aider/website/",
        ":!scripts/",
        ":!HISTORY.md",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def main():
    # Get the git log output
    diff_content = run_git_log()

    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".diff") as tmp:
        tmp.write(diff_content)
        tmp_path = tmp.name

    # Run blame to get aider percentage
    blame_result = subprocess.run(["python3", "scripts/blame.py"], capture_output=True, text=True)
    aider_line = blame_result.stdout.strip().split("\n")[-1]  # Get last line with percentage

    # Construct and run the aider command
    message = f"""
Update the history with changes shown in the diffs.
Describe actual user-facing changes, not every single commit that was made implementing them.
Don't edit or duplicate changes that have existing history entries, just add any new items not already listed.
Be sure to attribute changes to the proper .x version.
Changes in the .x-dev version should be listed under a "### main branch" heading

Also, add this as the last bullet under the "### main branch" section:
{aider_line}
"""  # noqa

    cmd = ["aider", "HISTORY.md", "--read", tmp_path, "--msg", message, "--no-auto-commit"]
    subprocess.run(cmd)

    # Run update-docs.sh after aider
    subprocess.run(["scripts/update-docs.sh"])

    # Cleanup
    os.unlink(tmp_path)


if __name__ == "__main__":
    main()
