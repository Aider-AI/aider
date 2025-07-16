import subprocess
import sys

from collections import defaultdict

# Length of abbreviated git hash used in blame output
hash_len = len("44e6fefc2")

def run(cmd):
    """Execute a git command and return its output.
    
    Args:
        cmd: List containing the command and its arguments
        
    Returns:
        String output of the command
    """
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout

def get_all_commit_hashes_between_tags(start_tag, end_tag=None):
    """Get all commit hashes between two tags or from a tag to HEAD.
    
    Args:
        start_tag: Starting tag or commit hash
        end_tag: Ending tag or commit hash (defaults to HEAD)
        
    Returns:
        List of commit hashes or None if no commits found
    """
    if end_tag:
        res = run(["git", "rev-list", f"{start_tag}..{end_tag}"])
    else:
        res = run(["git", "rev-list", f"{start_tag}..HEAD"])

    if res:
        commit_hashes = res.strip().split("\n")
        return commit_hashes
    return None

def get_commit_authors(commits):
    """Map commit hashes to their authors, marking aider-generated commits.
    
    Args:
        commits: List of commit hashes
        
    Returns:
        Dictionary mapping commit hashes to author names
    """
    commit_to_author = dict()
    for commit in commits:
        author = run(["git", "show", "-s", "--format=%an", commit]).strip()
        commit_message = run(["git", "show", "-s", "--format=%s", commit]).strip()
        if commit_message.lower().startswith("aider:"):
            author += " (aider)"
        commit_to_author[commit] = author
    return commit_to_author

def get_counts_for_file(start_tag, end_tag, authors, fname):
    """Count lines attributed to each author in a file using git blame.
    
    Args:
        start_tag: Starting tag or commit hash
        end_tag: Ending tag or commit hash (defaults to HEAD)
        authors: Dictionary mapping commit hashes to author names
        fname: File path to analyze
        
    Returns:
        Dictionary mapping author names to line counts, or None if file not found
    """
    try:
        if end_tag:
            text = run(
                [
                    "git",
                    "blame",
                    "-M100",  # Detect moved lines within a file with 100% similarity
                    "-C100",  # Detect moves across files with 100% similarity
                    "-C",  # Increase detection effort
                    "-C",  # Increase detection effort even more
                    "--abbrev=9",
                    f"{start_tag}..{end_tag}",
                    "--",
                    fname,
                ]
            )
        else:
            text = run(
                [
                    "git",
                    "blame",
                    "-M100",  # Detect moved lines within a file with 100% similarity
                    "-C100",  # Detect moves across files with 100% similarity
                    "-C",  # Increase detection effort
                    "-C",  # Increase detection effort even more
                    "--abbrev=9",
                    f"{start_tag}..HEAD",
                    "--",
                    fname,
                ]
            )
        if not text:
            return None
        text = text.splitlines()
        line_counts = defaultdict(int)
        for line in text:
            if line.startswith("^"):
                continue
            hsh = line[:hash_len]
            author = authors.get(hsh, "Unknown")
            line_counts[author] += 1

        return dict(line_counts)
    except subprocess.CalledProcessError as e:
        if "no such path" in str(e).lower():
            # File doesn't exist in this revision range, which is okay
            return None
        else:
            # Some other error occurred
            print(f"Warning: Unable to blame file {fname}. Error: {e}", file=sys.stderr)
            return None
