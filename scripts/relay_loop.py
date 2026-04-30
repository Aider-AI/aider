#!/usr/bin/env python3
"""
Minimal relay loop — routes a coding task through providers,
switching on exhaustion with git-only context handoff (KB-2026-007 Phase 1).

Usage:
    python scripts/relay_loop.py "add a hello world function to utils.py"
    python scripts/relay_loop.py --primary codex --fallback claude "refactor foo.py"
"""
import argparse
import asyncio
import subprocess
import sys

from aider.providers.base import BaseProvider
from aider.providers.claude_code import ClaudeCodeProvider
from aider.providers.codex import CodexProvider


def make_provider(name: str) -> BaseProvider:
    if name == "codex":
        return CodexProvider()
    if name == "claude":
        return ClaudeCodeProvider()
    raise ValueError(f"Unknown provider: {name}")


_MAX_DIFF_CHARS = 8_000


def git_context() -> str:
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


def handoff_prompt(task: str) -> str:
    return (
        "You are continuing a coding task in this repository. "
        "A previous AI assistant was working on this and hit its usage limit.\n\n"
        f"## Task\n{task}\n\n"
        f"## What has been done (from git)\n{git_context()}\n\n"
        "Please continue from where the previous assistant left off."
    )


async def run_turn(provider: BaseProvider, prompt: str, label: str) -> str | None:
    """Run one provider turn. Returns 'exhausted' if limit hit, None on success."""
    print(f"\n[{label}] ", end="", flush=True)
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


async def relay(task: str, primary: str, fallback: str, sim_exhaust_after: int = 0) -> None:
    providers = {primary: make_provider(primary), fallback: make_provider(fallback)}
    active = primary
    prompt = task
    exhausted_count = 0
    turn_counts: dict[str, int] = {primary: 0, fallback: 0}

    while True:
        label = active.upper()
        result = await run_turn(providers[active], prompt, label)

        if result is None:
            turn_counts[active] += 1

        # Simulate exhaustion after N turns on the current provider
        if result is None and sim_exhaust_after > 0 and turn_counts[active] >= sim_exhaust_after:
            other = fallback if active == primary else primary
            print(
                f"\n[RELAY] (sim) Simulating exhaustion after {sim_exhaust_after} turn(s) on"
                f" {label}. Switching to {other.upper()}..."
            )
            result = "exhausted"

        if result == "exhausted":
            exhausted_count += 1
            if exhausted_count >= 2:
                print("\n[RELAY] Both providers exhausted. Stopping.")
                break
            other = fallback if active == primary else primary
            print(f"[RELAY] Switching to {other.upper()}...")
            active = other
            prompt = handoff_prompt(task)
        else:
            try:
                next_input = input("\nYou: ").strip()
            except EOFError:
                break
            if not next_input:
                break
            prompt = next_input


def main():
    parser = argparse.ArgumentParser(description="aider-relay minimal relay loop")
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
    args = parser.parse_args()

    if args.primary == args.fallback:
        print("Primary and fallback must be different providers.")
        sys.exit(1)

    task = args.task or input("Task: ").strip()
    if not task:
        print("No task provided.")
        sys.exit(1)

    print(f"[RELAY] Primary: {args.primary.upper()} | Fallback: {args.fallback.upper()}")
    print(f"[RELAY] Task: {task}")

    asyncio.run(relay(task, args.primary, args.fallback, args.sim_exhaust_after))


if __name__ == "__main__":
    main()
