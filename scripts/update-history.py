#!/usr/bin/env python3

import os
import re
import subprocess
import tempfile

from history_prompts import history_prompt


def get_latest_version_from_history():
    with open("HISTORY.md", "r") as f:
        history_content = f.read()

    # Find most recent version header
    match = re.search(r"### Aider v(\d+\.\d+\.\d+)", history_content)
    if not match:
        raise ValueError("Could not find version header in HISTORY.md")
    return match.group(1)


def run_git_log():
    latest_ver = get_latest_version_from_history()
    cmd = [
        "git",
        "log",
        "--pretty=full",
        f"v{latest_ver}..HEAD",
        "--",
        "aider/",
        ":!aider/website/",
        ":!scripts/",
        ":!HISTORY.md",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def run_git_diff():
    latest_ver = get_latest_version_from_history()
    cmd = [
        "git",
        "diff",
        f"v{latest_ver}..HEAD",
        "--",
        "aider/",
        ":!aider/website/",
        ":!scripts/",
        ":!HISTORY.md",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def run_plain_git_log():
    latest_ver = get_latest_version_from_history()
    cmd = [
        "git",
        "log",
        f"v{latest_ver}..HEAD",
        "--",
        "aider/",
        ":!aider/website/",
        ":!scripts/",
        ":!HISTORY.md",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout


def main():
    # Get the git log and diff output
    log_content = run_git_log()
    plain_log_content = run_plain_git_log()
    diff_content = run_git_diff()

    # Extract relevant portion of HISTORY.md
    latest_ver = get_latest_version_from_history()
    with open("HISTORY.md", "r") as f:
        history_content = f.read()

    # Find the section for this version
    version_header = f"### Aider v{latest_ver}"
    start_idx = history_content.find("# Release history")
    if start_idx == -1:
        raise ValueError("Could not find start of release history")

    # Find where this version's section ends
    version_idx = history_content.find(version_header, start_idx)
    if version_idx == -1:
        raise ValueError(f"Could not find version header: {version_header}")

    # Find the next version header after this one
    next_version_idx = history_content.find("\n### Aider v", version_idx + len(version_header))
    if next_version_idx == -1:
        # No next version found, use the rest of the file
        relevant_history = history_content[start_idx:]
    else:
        # Extract just up to the next version
        relevant_history = history_content[start_idx:next_version_idx]

    # Save relevant portions to temporary files
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tmp_log:
        tmp_log.write(log_content)
        log_path = tmp_log.name

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".diff") as tmp_diff:
        tmp_diff.write(diff_content)
        diff_path = tmp_diff.name

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".plain_log") as tmp_plain_log:
        tmp_plain_log.write(plain_log_content)
        plain_log_path = tmp_plain_log.name

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as tmp_hist:
        tmp_hist.write(relevant_history)
        hist_path = tmp_hist.name

    # Run blame to get aider percentage
    blame_result = subprocess.run(["python3", "scripts/blame.py"], capture_output=True, text=True)
    aider_line = blame_result.stdout.strip().split("\n")[-1]  # Get last line with percentage

    # Construct and run the aider command
    message = history_prompt.format(aider_line=aider_line)

    cmd = [
        "aider",
        hist_path,
        "--read",
        log_path,
        "--read",
        plain_log_path,
        "--read",
        diff_path,
        "--msg",
        message,
        "--no-git",
        "--no-auto-lint",
    ]
    subprocess.run(cmd)

    # Read back the updated history
    with open(hist_path, "r") as f:
        updated_history = f.read()

    # Find where the next version section would start
    if next_version_idx == -1:
        # No next version found, use the rest of the file
        full_history = history_content[:start_idx] + updated_history
    else:
        # Splice the updated portion back in between the unchanged parts
        full_history = (
            history_content[:start_idx]
            + updated_history  # Keep unchanged header
            + history_content[next_version_idx:]  # Add updated portion  # Keep older entries
        )

    # Write back the full history
    with open("HISTORY.md", "w") as f:
        f.write(full_history)

    # Run update-docs.sh after aider
    subprocess.run(["scripts/update-docs.sh"])

    # Cleanup
    os.unlink(log_path)
    os.unlink(plain_log_path)
    os.unlink(diff_path)
    os.unlink(hist_path)

    # Show git diff of HISTORY.md
    subprocess.run(["git", "diff", "HISTORY.md"])


if __name__ == "__main__":
    main()
