"""
aider.macro_runner
==================

Implements the `/macro` command:

    /macro my_macro.py [k=v ...]

* Loads the target module (path or import‑able name)
* Finds a generator function `main(ctx, **kwargs)`
* Streams every value it yields back into Aider:
    • strings beginning with '/', '!' or '>' are treated exactly
      as if the user had typed them
* `ctx` is a mutable dict with:
      vars, registers, counters, exit_code, coder, io, send()

Helper utilities (log/run/code/include) live in this same file and are
re‑exported as the pseudo‑package **aider.helpers**.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import inspect
import os
import shlex
import sys
import types
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

###############################################################################
# Helper API  –  exposed to macro authors
###############################################################################

def log(text: str) -> str:
    """Return a chat log line (`> message`) ready to yield."""
    return text if text.startswith(">") else f"> {text}"

def run(cmd: str, *, capture: Optional[str] = None) -> Generator[str, str | None, str | None]:
    """
    Generator helper: `reply = yield from run("pytest -q", capture="t_out")`
    Adds optional `>capture` suffix so /run puts stdout in a register.
    """
    suffix = f" >{capture}" if capture else ""
    result = yield f"! {cmd}{suffix}"
    return result

def code(file: str, prompt: str) -> Generator[str, str | None, str | None]:
    """Edit a file with /code and return the model reply."""
    # Escape bare '}' so curly braces survive .format() inside /code handler
    safe = prompt.replace("}", "\\}")
    result = yield f"/code {file} {{{safe}}}"
    return result

def include(register: str) -> str:
    """Return a /include directive."""
    return f"/include {register}"

###############################################################################
# Runtime – invoked by commands.cmd_macro
###############################################################################

def _parse_argline(argline: str) -> tuple[str, Dict[str, str]]:
    """
    Splits the argline into  (module_path_or_name, kwargs_dict).
    Example:
        "examples/render_loop.py req='Render a dog'" ->
            ("examples/render_loop.py", {"req": "Render a dog"})
    """
    parts = shlex.split(argline)
    if not parts:
        raise ValueError("missing module path")
    mod = parts[0]
    kwargs: Dict[str, str] = {}
    for token in parts[1:]:
        if "=" not in token:
            raise ValueError(f"malformed argument '{token}', expected key=value")
        k, v = token.split("=", 1)
        kwargs[k] = v
    return mod, kwargs

def _import_module(modpath: str):
    """
    If `modpath` is a file ending in .py, import it by absolute path.
    Otherwise treat as regular importable module name.
    """
    if modpath.endswith(".py") or Path(modpath).exists():
        path = Path(modpath).expanduser().resolve()
        name = path.stem + "_macro"
        loader = importlib.machinery.SourceFileLoader(name, str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)  # type: ignore[arg-type]
        return module
    return importlib.import_module(modpath)

def _dispatch_action(commands, action: str) -> Any:
    """
    Send the action back through Aider.  Returns whatever the command handler
    (or coder) returns so we can forward it into the generator.
    """
    # '/...' or '! ...' handled directly via Commands.run()
    if action.startswith("/") or action.startswith("!"):
        return commands.run(action)

    # '> ' prompt → send to model as user question (no file edits)
    if action.startswith(">"):
        prompt = action[1:].lstrip()
        return commands.coder.run(prompt)

    # Fallback: treat as raw command (let Commands handle error)
    return commands.run(action)

def run_macro(commands, argline: str) -> None:
    """
    Entry‑point called by cmd_macro.  Parses args, imports module,
    builds ctx, runs the generator, streams its actions.
    """
    io = commands.io

    try:
        mod_path, kwargs = _parse_argline(argline)
    except ValueError as e:
        io.tool_error(str(e))
        return

    try:
        module = _import_module(mod_path)
    except FileNotFoundError:
        io.tool_error(f"macro file '{mod_path}' not found")
        return
    except Exception as e:
        io.tool_error(f"failed to import '{mod_path}': {e}")
        return

    main = getattr(module, "main", None)
    if not callable(main):
        io.tool_error(f"'{mod_path}' has no callable main()")
        return
    if not inspect.isgeneratorfunction(main):
        io.tool_error("main() must be a generator function (use 'yield')")
        return

    # Build execution context accessible inside the macro
    ctx: Dict[str, Any] = {
        "vars": kwargs.copy(),
        "registers": {},          # stdout/stderr buckets
        "counters": {},
        "exit_code": 0,
        "coder": commands.coder,
        "io": io,
        "send": commands.run,     # macro can call ctx["send"]("/run ls")
    }

    gen = main(ctx, **kwargs)    # type: ignore[arg-type]

    try:
        action = next(gen)       # prime the generator
        while True:
            result = _dispatch_action(commands, action)
            action = gen.send(result)
    except StopIteration:
        pass
    except Exception as e:
        io.tool_error(f"macro runtime error: {e}")

###############################################################################
# Expose helpers as virtual module  aider.helpers
###############################################################################

_helpers_mod = types.ModuleType("aider.helpers")
_helpers_mod.log = log
_helpers_mod.run = run
_helpers_mod.code = code
_helpers_mod.include = include
sys.modules["aider.helpers"] = _helpers_mod   # importable everywhere
