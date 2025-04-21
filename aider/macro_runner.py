"""
aider.macro_runner — runtime for the /macro command
===================================================

  /macro my_macro.py k1=v1 k2=v2 ...

• Imports the target module (file path or dotted name).
• Finds a *generator* main(ctx, **kwargs).
• Streams each yield back into Aider.
• Provides helpers (log/run/code/include) so macro code stays clean.

This file RE‑EXPORTS the helpers as `aider.helpers`.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import inspect
import os
import shlex
import sys
import types
from pathlib import Path
from typing import Any, Dict, Generator, Optional

# --------------------------------------------------------------------------- #
# Helper API used by macro authors                                            #
# --------------------------------------------------------------------------- #

def log(text: str) -> str:
    """Print a line to the user’s console (never sent to the LLM)."""
    return f"# {text}"

def run(cmd: str, *, capture: Optional[str] = None
        ) -> Generator[str, str | None, str | None]:
    """Yield a shell command; return its captured stdout/stderr."""
    suffix = f" >{capture}" if capture else ""
    result = yield f"! {cmd}{suffix}"
    return result

def code(file: str, prompt: str
         ) -> Generator[str, str | None, str | None]:
    """Ask the model to edit a file; return the model’s reply."""
    safe = prompt.replace("}", "\\}")
    result = yield f"/code {file} {{{safe}}}"
    return result

def include(register: str) -> str:
    """Include a register’s contents in the chat."""
    return f"/include {register}"

# --------------------------------------------------------------------------- #
# Argument parsing & module loading                                           #
# --------------------------------------------------------------------------- #

def _maybe_num(v: str) -> int | float | str:
    if v.isdigit() or (v.startswith('-') and v[1:].isdigit()):
        return int(v)
    try:
        return float(v)
    except ValueError:
        return v

def _parse_argline(argline: str) -> tuple[str, Dict[str, Any]]:
    parts = shlex.split(argline)
    if not parts:
        raise ValueError("missing module path")
    mod = parts[0]
    kwargs: Dict[str, Any] = {}
    for token in parts[1:]:
        if "=" not in token:
            raise ValueError(f"bad arg '{token}', expected k=v")
        k, v = token.split("=", 1)
        kwargs[k] = _maybe_num(v)
    return mod, kwargs

def _import_module(spec: str):
    if spec.endswith(".py") or Path(spec).exists():
        path = Path(spec).expanduser().resolve()
        name = path.stem + "_macro"
        loader = importlib.machinery.SourceFileLoader(name, str(path))
        module = importlib.util.module_from_spec(
            importlib.util.spec_from_loader(name, loader))  # type: ignore[arg-type]
        loader.exec_module(module)  # type: ignore[arg-type]
        return module
    return importlib.import_module(spec)

# --------------------------------------------------------------------------- #
# Dispatch an action produced by the macro generator                          #
# --------------------------------------------------------------------------- #

def _dispatch_action(commands, action: str):
    """
    Route the yielded `action` back into Aider and return the result
    (if any) to the generator.
    """
    if action.startswith("/") or action.startswith("!"):
        return commands.run(action)             # regular command

    if action.startswith("# "):                 # console‑only log
        commands.io.tool_output(action[2:])
        return None

    if action.startswith(">"):                  # prompt to the model
        prompt = action[1:].lstrip()
        return commands.coder.run(prompt)

    # fallback (unlikely)
    return commands.run(action)

# --------------------------------------------------------------------------- #
# Public entry‑point called by cmd_macro                                      #
# --------------------------------------------------------------------------- #

def run_macro(commands, argline: str) -> None:
    io = commands.io
    try:
        mod_spec, kwargs = _parse_argline(argline)
    except ValueError as e:
        io.tool_error(str(e))
        return

    try:
        module = _import_module(mod_spec)
    except Exception as e:
        io.tool_error(f"import failed: {e}")
        return

    main = getattr(module, "main", None)
    if not callable(main) or not inspect.isgeneratorfunction(main):
        io.tool_error("macro needs a generator main(ctx, **kwargs)")
        return

    ctx: Dict[str, Any] = {
        "vars": kwargs.copy(),
        "registers": {},
        "counters": {},
        "exit_code": 0,
        "coder": commands.coder,
        "io": io,
        "send": commands.run,
    }

    gen = main(ctx, **kwargs)  # type: ignore[arg-type]

    try:
        action = next(gen)
        while True:
            result = _dispatch_action(commands, action)
            action = gen.send(result)
    except StopIteration:
        pass
    except Exception as e:
        io.tool_error(f"macro runtime error: {e}")

# --------------------------------------------------------------------------- #
# Export helpers as virtual module aider.helpers                              #
# --------------------------------------------------------------------------- #

_helpers = types.ModuleType("aider.helpers")
_helpers.log = log
_helpers.run = run
_helpers.code = code
_helpers.include = include
sys.modules["aider.helpers"] = _helpers
