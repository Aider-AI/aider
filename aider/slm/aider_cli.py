from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run_aider_once(
    *,
    repo_path: str,
    prompt: str,
    rules_path: str | None,
    model: str | None,
    editor_model: str | None,
    weak_model: str | None,
    architect: bool,
    files: list[str] | None = None,
) -> None:
    """Run a single Aider instruction in non-interactive mode.

    We run Aider as a subprocess to keep the FastAPI worker stable and isolated.

    The prompt may include in-chat commands like `/code ...`.
    """

    cmd: list[str] = [
        "aider",
        "--yes-always",
        "--no-pretty",
        "--no-stream",
        "--no-auto-commits",
        "--no-dirty-commits",
    ]

    if model:
        cmd += ["--model", model]

    if weak_model:
        cmd += ["--weak-model", weak_model]

    if editor_model:
        cmd += ["--editor-model", editor_model]

    if architect:
        cmd += ["--architect"]

    if rules_path and Path(rules_path).exists():
        cmd += ["--read", rules_path]

    cmd += ["--message", prompt]

    # If prompt references specific files, we can help Aider by explicitly adding them.
    if files:
        cmd += list(files)

    # `--yes-always` ensures it proceeds if it still prompts.

    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")

    subprocess.run(cmd, cwd=repo_path, check=True, env=env)
