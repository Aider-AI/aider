"""
aider.macro_runner
==================

Runtime engine for the /macro command.

Usage inside Aider
------------------
    /macro path/to/macro.py loops=3 foo=bar

The file (or dotted module) must expose a generator:

    def main(ctx, **kwargs):
        ...
        yield from aider.helpers.run("echo hi", capture="msg")
        yield aider.helpers.log("Done")

Helper wrappers (log/run/code/include) are defined below and re‑exported as
`aider.helpers`.
"""

from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import inspect
import shlex
import sys
import types
from pathlib import Path
from typing import Any, Dict, Generator, Optional

# ----------------------------------------------------------------------------
# Helper API – macro authors import these from `aider.helpers`
# ----------------------------------------------------------------------------

def log(text: str) -> str:
    """Write a line to the console only (never sent to the LLM)."""
    return f"# {text}"

# --------------------------------------------------------------------- #
# Conversation / utility helpers                                        #
# --------------------------------------------------------------------- #

def chat(prompt: str) -> str:
    """
    Send a plain user message to the main model without editing files.
    Equivalent to typing the prompt at the Aider prompt.
    """
    return f"> {prompt}"

def ask(prompt: str) -> str:
    """
    Use Aider’s /ask command (questions about the code base, no edits).
    """
    return f"/ask {prompt}"

def search(query: str, *, max_results: int = 5, model_suffix=":online") -> str:
    """
    Yield a sequence that:
      1. remembers the current model
      2. switches to the same model with ':online' (or custom plugin cfg)
      3. asks the query
      4. restores the previous model

    Example inside a macro::

        hits = yield from ah.search("python asyncio graceful shutdown")
        yield ah.log(hits)
    """

    # Prepare the model-switch commands
    set_online   = f"/model +{model_suffix}"
    restore_prev = "/model -"          # built‑in: reverts to previous

    # Compose multi‑line action: switch → ask → restore
    # Each line will be executed sequentially by _dispatch_action
    ask_line = f"> {query}"
    return "\n".join([set_online, ask_line, restore_prev])


def run(cmd: str, *, capture: Optional[str] = None
        ) -> Generator[str, str | None, str | None]:
    """
    Shell helper::

        out = yield from ah.run('pytest -q', capture='t_out')
    """
    suffix = f" >{capture}" if capture else ""
    result = yield f"! {cmd}{suffix}"
    return result

def code(file: str, prompt: str
         ) -> Generator[str, str | None, str | None]:
    """
    File‑edit helper::

        reply = yield from ah.code('scene.json', 'Fix the bug')
    """
    safe = prompt.replace("}", "\\}")
    result = yield f"/code {file} {{{safe}}}"
    return result

def include(register: str) -> str:
    """Include a register’s contents in the chat."""
    return f"/include {register}"

# --------------------------------------------------------------------- #
#  Spawn helper – run any action in the background, stay silent         #
# --------------------------------------------------------------------- #
import concurrent.futures
_EXEC = concurrent.futures.ThreadPoolExecutor(max_workers=8)
_SPAWN_CMDS = None  # set inside run_macro()

def _run_action_silent(commands, action: str):
    """
    Execute one macro action but suppress all UI output.
    We reuse _dispatch_action so *any* slash/!/> string works.
    """
    # Temporarily silence tool_output to avoid console noise
    io = commands.io
    original = io.tool_output
    io.tool_output = lambda *a, **kw: None
    try:
        return _dispatch_action(commands, action)
    finally:
        io.tool_output = original

def spawn(action: str):
    """
    Run `action` asynchronously with no console output.
    Example use inside a macro::

        fut = ah.spawn("/ask How many routes are defined?")
        ... do other work ...
        answer = fut.result()
    """
    return _EXEC.submit(_run_action_silent, _SPAWN_CMDS, action)


# ----------------------------------------------------------------------------
# Internal utilities
# ----------------------------------------------------------------------------

def _maybe_num(v: str) -> int | float | str:
    """Best‑effort cast of CLI values to int/float."""
    if v.isdigit() or (v.startswith('-') and v[1:].isdigit()):
        return int(v)
    try:
        return float(v)
    except ValueError:
        return v

def _parse_argline(argline: str) -> tuple[str, Dict[str, Any]]:
    parts = shlex.split(argline)
    if not parts:
        raise ValueError("Missing module path")
    mod = parts[0]
    kwargs: Dict[str, Any] = {}
    for token in parts[1:]:
        if "=" not in token:
            raise ValueError(f"Bad arg '{token}', expected k=v")
        k, v = token.split("=", 1)
        kwargs[k] = _maybe_num(v)
    return mod, kwargs

def _import_module(spec: str):
    """
    Import by absolute .py path or dotted module name.
    """
    if spec.endswith(".py") or Path(spec).exists():
        path = Path(spec).expanduser().resolve()
        name = path.stem + "_macro"
        loader = importlib.machinery.SourceFileLoader(name, str(path))
        module = importlib.util.module_from_spec(
            importlib.util.spec_from_loader(name, loader))  # type: ignore[arg-type]
        loader.exec_module(module)  # type: ignore[arg-type]
        return module
    return importlib.import_module(spec)

def _dispatch_action(commands, action: str):
    """
    Route a yielded action back through Aider and return the result
    to the generator.
    """
    if action.startswith("/") or action.startswith("!"):
        return commands.run(action)

    if action.startswith("# "):                       # console log
        commands.io.tool_output(action[2:])
        return None

    if action.startswith(">"):                       # prompt → LLM
        prompt = action[1:].lstrip()
        return commands.coder.run(prompt)

    # Fallback: treat as command string (lets user yield raw /add … etc.)
    return commands.run(action)

# ----------------------------------------------------------------------------
# Entry point invoked by Commands.cmd_macro
# ----------------------------------------------------------------------------

def run_macro(commands, argline: str) -> None:
    io = commands.io

    try:
        mod_spec, kwargs = _parse_argline(argline)
    except ValueError as err:
        io.tool_error(str(err))
        return

    try:
        module = _import_module(mod_spec)
    except Exception as err:
        io.tool_error(f"Import failed: {err}")
        return

    main = getattr(module, "main", None)
    if not callable(main) or not inspect.isgeneratorfunction(main):
        # ───────── clearer debug block ─────────
        io.tool_error(
            "=== [Error Debug: Macro] ===\n"
            f"- Filename: {mod_spec}\n"
            "- Problem : macro must define a *generator* "
            "main(ctx, **kwargs)\n"
            "- File preview below ↓ (first 20 lines)\n"
            "========================================"
        )
        try:
            with open(Path(mod_spec).expanduser().resolve(), "r") as fh:
                preview = "".join([next(fh) for _ in range(20)])
            sep = "…" if len(preview.splitlines()) == 20 else ""
            io.tool_output(preview + sep +
                           "\n=== [End Debug] ===")
        except Exception as e:
            io.tool_output(f"(could not read file: {e})\n=== [End Debug] ===")
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

    global _SPAWN_CMDS
    _SPAWN_CMDS = commands

    gen = main(ctx, **kwargs)  # type: ignore[arg-type]

    try:
        action = next(gen)                     # prime
        while True:
            result = _dispatch_action(commands, action)
            action = gen.send(result)
    except StopIteration:
        pass
    except Exception as err:
        io.tool_error(f"Macro runtime error: {err}")

# ----------------------------------------------------------------------------
# Re‑export helpers as `aider.helpers`
# ----------------------------------------------------------------------------

_helpers = types.ModuleType("aider.helpers")
_helpers.log = log
_helpers.run = run
_helpers.code = code
_helpers.include = include
_helpers.chat = chat
_helpers.ask = ask
_helpers.search = search
_helpers.spawn = spawn
sys.modules["aider.helpers"] = _helpers
