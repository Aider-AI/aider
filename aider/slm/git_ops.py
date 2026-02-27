from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Tuple


def _run(cmd: list[str], *, cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def ensure_repo_ready(repo_path: str, repo_git_url: str | None, push_remote: str) -> None:
    """Ensure repo_path exists and is a git repo.

    If repo_path is missing and repo_git_url is provided, it will be cloned.
    """

    p = Path(repo_path)
    if not p.exists():
        if not repo_git_url:
            raise RuntimeError(
                f"Repo path {repo_path} does not exist and SLM_REPO_GIT_URL was not set"
            )
        p.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "clone", repo_git_url, repo_path])

    if not (p / ".git").exists():
        raise RuntimeError(f"{repo_path} is not a git repository")

    # Ensure remote exists.
    remotes = _run(["git", "-C", repo_path, "remote"], check=True).stdout.split()
    if push_remote not in remotes:
        raise RuntimeError(
            f"Expected git remote '{push_remote}' to exist. Found: {', '.join(remotes)}"
        )

    # Fetch base branch refs so we can reset to origin/main.
    _run(["git", "-C", repo_path, "fetch", push_remote, "--prune"], check=True)


def reset_hard(repo_path: str, ref: str) -> None:
    _run(["git", "-C", repo_path, "reset", "--hard", ref], check=True)
    # Remove untracked files so each run starts clean.
    subprocess.run(
        ["git", "-C", repo_path, "clean", "-fd"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def get_commit(repo_path: str) -> str:
    return _run(["git", "-C", repo_path, "rev-parse", "HEAD"], check=True).stdout.strip()


def get_branch(repo_path: str) -> str:
    return _run(["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"], check=True).stdout.strip()


def git_has_changes(repo_path: str) -> bool:
    # staged/unstaged changes?
    res = subprocess.run(
        ["git", "-C", repo_path, "diff", "--quiet"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if res.returncode == 1:
        return True

    res = subprocess.run(
        ["git", "-C", repo_path, "diff", "--cached", "--quiet"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return res.returncode == 1


def get_diff_stat(repo_path: str) -> str:
    return _run(["git", "-C", repo_path, "diff", "--stat"], check=True).stdout.strip()


def run_sanity_checks(repo_path: str, *, cargo_cmd: str, forge_cmd: str) -> tuple[bool, str | None]:
    """Run cargo check/forge test if they seem applicable.

    This is best-effort: if the repo doesn't look like a Rust or Foundry project, skip.
    """

    # cargo
    if (Path(repo_path) / "Cargo.toml").exists():
        ok, err = _run_shell(repo_path, cargo_cmd)
        if not ok:
            return False, f"cargo check failed: {err}"

    # foundry
    if (Path(repo_path) / "foundry.toml").exists() or (Path(repo_path) / "lib").exists():
        ok, err = _run_shell(repo_path, forge_cmd)
        if not ok:
            return False, f"forge test failed: {err}"

    return True, None


def _run_shell(repo_path: str, cmd: str) -> tuple[bool, str | None]:
    proc = subprocess.run(
        cmd,
        cwd=repo_path,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode == 0:
        return True, None
    return False, proc.stdout[-8000:] if proc.stdout else f"exit code {proc.returncode}"


def stage_commit_and_push(
    repo_path: str,
    *,
    branch: str,
    base_branch: str,
    push_remote: str,
    github_token: str | None,
    commit_message: str,
) -> Tuple[bool, str | None, str | None]:
    """Commit changes and push to base_branch.

    Strategy:
      1) Commit on the working branch
      2) Fetch origin/base
      3) Rebase branch onto origin/base
      4) Fast-forward merge into local base branch
      5) Push base branch

    Returns: (ok, err, commit_sha)
    """

    # Ensure we have changes
    if not git_has_changes(repo_path):
        return True, None, None

    _run(["git", "-C", repo_path, "add", "-A"], check=True)

    # Provide a default identity if none configured.
    _run(
        [
            "git",
            "-C",
            repo_path,
            "-c",
            "user.name=slm",
            "-c",
            "user.email=slm@localhost",
            "commit",
            "-m",
            commit_message,
        ],
        check=True,
    )
    commit_sha = get_commit(repo_path)

    # Rebase branch onto latest origin/base_branch
    _run(["git", "-C", repo_path, "fetch", push_remote, base_branch], check=True)
    rebase = subprocess.run(
        ["git", "-C", repo_path, "rebase", f"{push_remote}/{base_branch}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if rebase.returncode != 0:
        subprocess.run(["git", "-C", repo_path, "rebase", "--abort"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False, "rebase failed (conflicts)", commit_sha

    # Update base branch locally
    _run(
        [
            "git",
            "-C",
            repo_path,
            "checkout",
            "-B",
            base_branch,
            f"{push_remote}/{base_branch}",
        ],
        check=True,
    )
    merge = subprocess.run(
        ["git", "-C", repo_path, "merge", "--ff-only", branch],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if merge.returncode != 0:
        return False, "fast-forward merge failed", commit_sha

    # Use github token for push if provided and remote is GitHub.
    if github_token:
        _ensure_github_push_url(repo_path, push_remote, github_token)

    push = subprocess.run(
        ["git", "-C", repo_path, "push", push_remote, base_branch],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if push.returncode != 0:
        return False, push.stdout[-8000:] if push.stdout else "git push failed", commit_sha

    return True, None, commit_sha


def _ensure_github_push_url(repo_path: str, remote: str, token: str) -> None:
    # Don't print the token.
    url = _run(["git", "-C", repo_path, "remote", "get-url", remote], check=True).stdout.strip()

    # Only attempt rewrite for GitHub remotes.
    m = re.search(r"github\.com[:/](?P<owner_repo>[^\s]+?)(?:\.git)?$", url)
    if not m:
        return

    owner_repo = m.group("owner_repo")
    push_url = f"https://x-access-token:{token}@github.com/{owner_repo}.git"
    subprocess.run(
        ["git", "-C", repo_path, "remote", "set-url", "--push", remote, push_url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


__all__ = [
    "ensure_repo_ready",
    "reset_hard",
    "get_commit",
    "get_branch",
    "git_has_changes",
    "get_diff_stat",
    "run_sanity_checks",
    "stage_commit_and_push",
]
