"""
Relay loop — routes a coding task through providers, switching on exhaustion
with MTARP session continuation (KB-2026-021/026/030).

Entry point for the installed `aider-relay` CLI command. Also importable as
a library: `from aider.relay.loop import relay`.

Usage (installed):
    aider-relay "add OAuth login"
    aider-relay --primary codex --fallback claude "refactor foo.py"
    aider-relay --autonomous --max-turns 20 --task-file TASK.md

Usage (source):
    python -m aider.relay.loop "add OAuth login"
    uv run aider-relay "add OAuth login"
"""
import argparse
import asyncio
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from aider.providers.base import BaseProvider
from aider.providers.claude_code import ClaudeCodeProvider
from aider.providers.codex import CodexProvider
from aider.relay.session import MTARPSession

_MAX_DIFF_CHARS = 8_000
_CONTINUATION_PROMPT = (
    "Continue working on the task. Check git log to see what has been committed. "
    "Keep going until the task is complete or you cannot proceed further."
)
_MERGE_REVIEW_PROMPT = (
    "Before this session ends, perform a self-review of your changes against these criteria:\n\n"
    "1. **Process artifacts** — Have you committed any relay-internal files (TASK.md, "
    "session.json, *.patch)? If so, remove them from the branch.\n"
    "2. **Doc/runtime alignment** — Every path, command, or output path you documented — "
    "does it match what the code actually produces? Run a check if needed.\n"
    "3. **Version consistency** — Do version strings in docs, configs, and changelogs agree?\n"
    "4. **Proof encoding** — Every proof claim ('test X passes') — is it encoded as a "
    "repo-owned automation step (CI task, test, Makefile target)?\n"
    "5. **Handoff envelope** — Ensure .aider-relay/session.json has non-empty "
    "files_in_scope and session_summary.\n\n"
    "Fix any issues found. If you cannot fix something, state why in a comment or TODO."
)


def make_provider(name: str) -> BaseProvider:
    if name == "codex":
        return CodexProvider()
    if name == "claude":
        return ClaudeCodeProvider()
    raise ValueError(f"Unknown provider: {name}")


def _try_make_git_repo():
    """Create a GitRepo for richer git operations. Returns None if unavailable."""
    try:
        from aider.io import InputOutput
        from aider.repo import GitRepo

        _io = InputOutput(pretty=False, yes=True)
        return GitRepo(io=_io, fnames=[], git_dname=str(Path.cwd()))
    except Exception:
        return None


def _files_changed(session: MTARPSession, git_repo) -> list[str]:
    """Return files changed between session start and current HEAD via git diff --name-only."""
    if not (git_repo and session.git_diff_since and session.git_head):
        return []
    try:
        raw = git_repo.repo.git.diff("--name-only", session.git_diff_since, session.git_head)
        return [f for f in raw.splitlines() if f.strip()]
    except Exception:
        return []


def _generate_summary(task: str, diff: str, model_name: str = "claude-haiku-4-5-20251001") -> str:
    """Generate a 2-3 sentence summary of what was accomplished. Returns '' on any failure."""
    if not diff.strip():
        return ""
    try:
        import litellm

        prompt = (
            f"Task: {task}\n\n"
            f"Git diff:\n{diff[:6000]}\n\n"
            "Summarise in 2-3 sentences what was accomplished. "
            "Be specific: mention file names and key changes."
        )
        response = litellm.completion(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return ""


def _build_repomap_context(session: MTARPSession, git_repo) -> str:
    """Return a RepoMap string for files changed during the session, or '' on any failure."""
    try:
        from aider.io import InputOutput
        from aider.models import Model
        from aider.repomap import RepoMap

        changed = session.files_in_scope or _files_changed(session, git_repo)
        all_files = list(git_repo.get_tracked_files())
        if not all_files:
            return ""

        io = InputOutput(pretty=False, yes=True)
        model = Model("claude-haiku-4-5-20251001")
        repo_map = RepoMap(map_tokens=2048, root=str(Path.cwd()), main_model=model, io=io)
        return repo_map.get_repo_map(chat_files=changed, other_files=all_files) or ""
    except Exception:
        return ""


def git_context(git_repo=None) -> str:
    if git_repo is not None:
        try:
            log = git_repo.repo.git.log("--oneline", "-10") or "(no git history)"
            diff = git_repo.get_diffs() or "(none)"
            if len(diff) > _MAX_DIFF_CHARS:
                diff = (
                    diff[:_MAX_DIFF_CHARS]
                    + f"\n... (truncated — {len(diff) - _MAX_DIFF_CHARS} chars omitted)"
                )
            return f"Recent git history:\n{log}\n\nCurrent uncommitted changes:\n{diff}"
        except Exception:
            pass  # fall through to subprocess

    def run(cmd):
        try:
            return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
        except (subprocess.CalledProcessError, OSError):
            return None

    log = run(["git", "log", "--oneline", "-10"]) or "(no git history)"
    diff = run(["git", "diff", "HEAD"]) or "(none)"
    if len(diff) > _MAX_DIFF_CHARS:
        diff = (
            diff[:_MAX_DIFF_CHARS]
            + f"\n... (truncated — {len(diff) - _MAX_DIFF_CHARS} chars omitted)"
        )
    return f"Recent git history:\n{log}\n\nCurrent uncommitted changes:\n{diff}"


def handoff_prompt(task: str, session: MTARPSession | None = None, git_repo=None) -> str:
    session_diff = None
    if git_repo and session and session.git_diff_since and session.git_head:
        try:
            session_diff = git_repo.diff_commits(False, session.git_diff_since, session.git_head)
            if len(session_diff) > _MAX_DIFF_CHARS:
                session_diff = (
                    session_diff[:_MAX_DIFF_CHARS]
                    + f"\n... (truncated — {len(session_diff) - _MAX_DIFF_CHARS} chars omitted)"
                )
        except Exception:
            session_diff = None

    if session_diff is not None:
        since = session.git_diff_since[:7]
        head = session.git_head[:7]
        context_section = (
            f"## What was done this session (git diff {since}..{head})\n"
            f"{session_diff or '(no changes committed)'}"
        )
    else:
        context_section = f"## What has been done (from git)\n{git_context(git_repo)}"

    repomap_section = ""
    if git_repo and session:
        repomap = _build_repomap_context(session, git_repo)
        if repomap:
            repomap_section = f"\n\n## Repository map (files touched this session)\n{repomap}"

    base = (
        "You are continuing a coding task in this repository. "
        "A previous AI assistant was working on this and hit its usage limit.\n\n"
        f"## Task\n{task}\n"
        f"{repomap_section}\n\n"
        f"{context_section}\n\n"
        "Please continue from where the previous assistant left off."
    )
    if session is not None:
        base += (
            "\n\n## MTARP Session Envelope\n"
            "A session record has been written to .aider-relay/session.json capturing the task,\n"
            "git state at handoff, and which provider was working. You can inspect it with:\n"
            "  cat .aider-relay/session.json"
        )
    return base


def _check_interrupt(session_dir: str) -> bool:
    """Return True (and remove sentinel) if .aider-relay/interrupt exists."""
    sentinel = Path(session_dir) / "interrupt"
    if sentinel.exists():
        sentinel.unlink()
        return True
    return False


async def _run_turn_events(provider: BaseProvider, prompt: str, label: str) -> str | None:
    async for event in provider.run_turn(prompt):
        if event.type == "text":
            print(event.content, end="", flush=True)
        elif event.type == "exhausted":
            suffix = f" (resets at {event.reset_at})" if event.reset_at else ""
            print(f"\n\n[{label}] Usage window exhausted{suffix}.")
            return "exhausted"
        elif event.type == "error":
            print(f"\n[{label}] Error: {event.content}")
        elif event.type == "done":
            print()
    return None


async def run_turn(
    provider: BaseProvider, prompt: str, label: str, turn_timeout: int = 0
) -> str | None:
    """Run one provider turn. Returns 'exhausted'/'timeout' if limit hit, None on success."""
    print(f"\n[{label}] ", end="", flush=True)
    coro = _run_turn_events(provider, prompt, label)
    if turn_timeout > 0:
        try:
            return await asyncio.wait_for(coro, timeout=turn_timeout)
        except asyncio.TimeoutError:
            print(f"\n[{label}] Turn timed out after {turn_timeout}s.")
            return "timeout"
    return await coro


async def relay(
    task: str,
    primary: str,
    fallback: str,
    sim_exhaust_after: int = 0,
    session_dir: str = ".aider-relay",
    autonomous: bool = False,
    max_turns: int = 0,
    turn_timeout: int = 0,
    merge_review: bool = False,
) -> None:
    git_repo = _try_make_git_repo()
    providers = {primary: make_provider(primary), fallback: make_provider(fallback)}
    active = primary
    prompt = task
    exhausted: set[str] = set()
    turn_counts: dict[str, int] = {primary: 0, fallback: 0}
    total_turns = 0

    session = MTARPSession.create(task=task, primary_provider=primary)
    provider_started_at = datetime.now(tz=timezone.utc).isoformat()

    while True:
        if _check_interrupt(session_dir):
            print("\n[RELAY] Interrupt sentinel detected. Stopping after current turn boundary.")
            break

        label = active.upper()
        result = await run_turn(providers[active], prompt, label, turn_timeout=turn_timeout)

        if result is None:
            turn_counts[active] += 1
            total_turns += 1

        if result is None and sim_exhaust_after > 0 and turn_counts[active] >= sim_exhaust_after:
            other = fallback if active == primary else primary
            print(
                f"\n[RELAY] (sim) Simulating exhaustion after {sim_exhaust_after} turn(s) on"
                f" {label}. Switching to {other.upper()}..."
            )
            result = "exhausted"

        if result in ("exhausted", "timeout"):
            exhausted.add(active)
            end_reason = result

            ended_at = datetime.now(tz=timezone.utc).isoformat()
            if git_repo:
                head = git_repo.get_head_commit_sha()
                if head:
                    session.git_head = head
            else:
                try:
                    session.git_head = subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
                    ).strip()
                except (subprocess.CalledProcessError, OSError):
                    pass

            session.files_in_scope = _files_changed(session, git_repo)
            diff_for_summary = ""
            if git_repo and session.git_diff_since and session.git_head:
                try:
                    diff_for_summary = (
                        git_repo.diff_commits(False, session.git_diff_since, session.git_head) or ""
                    )
                except Exception:
                    pass
            session.session_summary = _generate_summary(task, diff_for_summary)

            for warning in session.validate_handoff():
                print(f"[RELAY] Warning: {warning}")

            session.add_provider_run(
                provider=active,
                tier=providers[active].tier,
                session_id=providers[active].current_session_id or "",
                started_at=provider_started_at,
                ended_at=ended_at,
                end_reason=end_reason,
            )
            session.outgoing_provider = active
            session.handoff_reason = end_reason
            session.handoff_at = ended_at
            session_path = Path(session_dir) / "session.json"
            session_path.parent.mkdir(parents=True, exist_ok=True)
            session.write(session_path)
            provider_started_at = datetime.now(tz=timezone.utc).isoformat()

            other = fallback if active == primary else primary
            if other in exhausted:
                print("\n[RELAY] Both providers exhausted. Stopping.")
                break
            print(f"[RELAY] Switching to {other.upper()}...")
            active = other
            prompt = handoff_prompt(task, session=session, git_repo=git_repo)

        else:
            if max_turns > 0 and total_turns >= max_turns:
                print(f"\n[RELAY] Reached max turns ({max_turns}). Stopping.")
                if merge_review:
                    print(f"[RELAY] Running merge-readiness review on {label}...")
                    await run_turn(
                        providers[active], _MERGE_REVIEW_PROMPT, label, turn_timeout=turn_timeout
                    )
                break

            if autonomous:
                prompt = _CONTINUATION_PROMPT
            else:
                try:
                    next_input = input("\nYou: ").strip()
                except EOFError:
                    if merge_review:
                        print(f"[RELAY] Running merge-readiness review on {label}...")
                        await run_turn(
                            providers[active],
                            _MERGE_REVIEW_PROMPT,
                            label,
                            turn_timeout=turn_timeout,
                        )
                    break
                if not next_input:
                    if merge_review:
                        print(f"[RELAY] Running merge-readiness review on {label}...")
                        await run_turn(
                            providers[active],
                            _MERGE_REVIEW_PROMPT,
                            label,
                            turn_timeout=turn_timeout,
                        )
                    break
                prompt = next_input


def main():
    parser = argparse.ArgumentParser(description="aider-relay: multi-provider relay loop")
    parser.add_argument("task", nargs="?", help="Initial task (prompted if omitted)")
    parser.add_argument("--primary", default="claude", choices=["claude", "codex"])
    parser.add_argument("--fallback", default="codex", choices=["claude", "codex"])
    parser.add_argument(
        "--sim-exhaust-after",
        type=int,
        default=0,
        metavar="N",
        help="Simulate exhaustion after N turns on each provider (0=disabled)",
    )
    parser.add_argument(
        "--autonomous",
        action="store_true",
        help="Run autonomously without waiting for user input between turns",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=0,
        metavar="N",
        help="Stop after N total turns across all providers (0=unlimited)",
    )
    parser.add_argument(
        "--task-file",
        metavar="PATH",
        help="Read initial task from a file (e.g. TASK.md)",
    )
    parser.add_argument(
        "--turn-timeout",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Kill a provider turn after N seconds and treat as exhausted (0=disabled)",
    )
    parser.add_argument(
        "--merge-review",
        action="store_true",
        help="Send a merge-readiness self-review prompt to the active provider before stopping",
    )
    parser.add_argument(
        "--exec-prefix",
        metavar="CMD",
        default="",
        help=(
            "Container exec gateway (e.g. 'podman exec mycontainer'). "
            "Prepended to the task as a system instruction so the agent knows "
            "all build/test/git-write commands must route through the container."
        ),
    )
    args = parser.parse_args()

    if args.primary == args.fallback:
        print("Primary and fallback must be different providers.")
        sys.exit(1)

    if args.task_file:
        task_path = Path(args.task_file)
        if not task_path.exists():
            print(f"Task file not found: {args.task_file}")
            sys.exit(1)
        task = task_path.read_text().strip()
    else:
        task = args.task or input("Task: ").strip()

    if not task:
        print("No task provided.")
        sys.exit(1)

    if args.exec_prefix:
        gateway_instruction = (
            "SYSTEM — EXECUTION GATEWAY\n"
            "All build, test, and git-write commands MUST run inside the container "
            f"via:\n\n  {args.exec_prefix} <command>\n\n"
            f"Example: `{args.exec_prefix} ./gradlew build`\n"
            "Direct execution of these commands on the host is blocked by the "
            "permission system. File reads/writes and git reads (status/log/diff) "
            "may be run on the host directly.\n\n---\n\n"
        )
        task = gateway_instruction + task

    print(f"[RELAY] Primary: {args.primary.upper()} | Fallback: {args.fallback.upper()}")
    if args.autonomous:
        limit = f" (max {args.max_turns} turns)" if args.max_turns else ""
        print(f"[RELAY] Mode: autonomous{limit}")
    print(f"[RELAY] Task: {task[:120]}{'...' if len(task) > 120 else ''}")

    asyncio.run(
        relay(
            task,
            args.primary,
            args.fallback,
            args.sim_exhaust_after,
            session_dir=".aider-relay",
            autonomous=args.autonomous,
            max_turns=args.max_turns,
            turn_timeout=args.turn_timeout,
            merge_review=args.merge_review,
        )
    )


if __name__ == "__main__":
    main()
