import subprocess

def get_aider_commits():
    """Get commit hashes for commits with messages starting with 'aider:'"""
    result = subprocess.run(
        ["git", "log", "--pretty=format:%H %s"],
        capture_output=True,
        text=True,
        check=True
    )
    commits = []
    for line in result.stdout.splitlines():
        commit_hash, commit_message = line.split(" ", 1)
        if commit_message.startswith("aider:"):
            commits.append(commit_hash)
    return commits

def get_blame_lines(commit_hash):
    """Get lines introduced by a specific commit"""
    result = subprocess.run(
        ["git", "blame", "--line-porcelain", commit_hash],
        capture_output=True,
        text=True,
        check=True
    )
    lines = []
    for line in result.stdout.splitlines():
        if line.startswith("author "):
            lines.append(line)
    return lines

def mark_aider_lines():
    """Mark lines introduced by 'aider:' commits"""
    aider_commits = get_aider_commits()
    for commit in aider_commits:
        blame_lines = get_blame_lines(commit)
        for line in blame_lines:
            print(f"AIDER: {line}")

if __name__ == "__main__":
    mark_aider_lines()
