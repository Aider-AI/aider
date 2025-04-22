"""
Dynamic loader/driver for user‑supplied Python macros.

Each macro **must** expose:

    def main(ctx: dict, **kwargs) -> None | Generator[str, Any, None]

`ctx` contains:
    io        – current InputOutput instance
    coder     – active Coder
    commands  – Commands dispatcher (so macros may emit slash‑commands)

If `main()` is a *generator*, every yielded string is sent through Aider’s
normal command pipeline and the resulting text is fed back into the generator,
enabling tight, two‑way loops.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Generator

# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #


class MacroSecurityError(RuntimeError):
    """Raised when a macro is blocked by security policy (allow‑list, etc)."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _check_allow_list(file_path: Path) -> None:
    allow_file = Path.home() / ".aider" / "macro.allowlist"
    if allow_file.exists():
        allowed = {ln.strip() for ln in allow_file.read_text().splitlines() if ln.strip()}
        if str(file_path) not in allowed:
            raise MacroSecurityError(
                f"{file_path} is not in ~/.aider/macro.allowlist – macro blocked"
            )


def _load_module(file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("aider_user_macro", file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load macro {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    return mod


# --------------------------------------------------------------------------- #
# Public entry‑point
# --------------------------------------------------------------------------- #


def run_macro(file_path: str | Path, ctx: dict[str, Any], **kwargs: Any) -> None:
    """
    Execute the macro at *file_path*.

    Parameters
    ----------
    file_path
        Path to a Python file that defines `main(ctx, **kwargs)`.
    ctx
        Runtime context dict – **MUST** contain keys: ``io``, ``coder``, ``commands``.
    **kwargs
        Arbitrary keyword arguments forwarded to the macro.
    """

    fp = Path(file_path).expanduser().resolve()
    if not fp.exists():
        raise FileNotFoundError(fp)

    _check_allow_list(fp)
    mod = _load_module(fp)

    main = getattr(mod, "main", None)
    if not callable(main):
        raise AttributeError(f"{fp} must define a callable `main(ctx, **kwargs)`")

    runner = main(ctx, **kwargs)

    # --- generator macro --------------------------------------------------- #
    if inspect.isgenerator(runner):
        result: Any = None
        while True:
            try:
                cmd = runner.send(result) if result is not None else next(runner)
            except StopIteration:
                break

            if isinstance(cmd, str) and cmd.strip():
                result = ctx["commands"].process_user_message(cmd)
            else:
                result = None

    # --- plain function macro --------------------------------------------- #
    else:
        # already executed through direct call – nothing else to do
        pass
