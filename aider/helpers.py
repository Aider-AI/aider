"""
Light-weight façade that macros import as **`ah`**.

All public helpers forward to the *current* MacroRunner instance to
keep macros decoupled from Aider internals.
"""

from __future__ import annotations

from concurrent.futures import Future
from typing import Any, List

__all__ = ["spawn", "gather", "log", "chat", "set_runner"]

# ------------------------------------------------------------------ #
# Runner plumbing (internal)                                         #
# ------------------------------------------------------------------ #

_runner: "MacroRunner | None" = None


def set_runner(runner: "MacroRunner | None") -> None:
    """Installed by MacroRunner at start/end of a `/macro` run."""
    global _runner
    _runner = runner


def _require_runner() -> "MacroRunner":
    if _runner is None:
        raise RuntimeError("aider.helpers used outside an active MacroRunner")
    return _runner


# ------------------------------------------------------------------ #
# Public helper API                                                  #
# ------------------------------------------------------------------ #

def spawn(prompt: str) -> Future:
    """Fire-and-forget LLM call; returns `Future[str]`."""
    return _require_runner().spawn(prompt)


def gather() -> List[str]:
    """Wait for *all* spawned jobs; returns their responses."""
    return _require_runner().gather()


def log(message: str) -> None:
    """Print a tool-style message to the shared console."""
    _require_runner().io.tool_output(message)


def chat(prompt: str) -> str:
    """
    Blocking LLM round-trip that also streams the reply to the console.
    Returns the raw assistant text.
    """
    runner = _require_runner()
    reply = runner.llm(prompt)
    runner.io.assistant_output(reply)
    return reply


# Legacy alias – keeps `import aider_helpers as ah` working
import sys as _sys

_sys.modules.setdefault("aider_helpers", _sys.modules[__name__])

