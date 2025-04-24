"""
aider.macro_runner
==================

Light-weight runtime engine for Aider’s **/macro** command.

    /macro path/to/macro.py loops=3 foo=bar

A *macro* is just a **generator** that can yield:

* a string starting with `/ …` or `! …` &nbsp;→ executed as an Aider slash-cmd or shell cmd  
* a string starting with `> …`                &nbsp;→ sent to the LLM as a plain prompt  
* `ah.log("…")`                              &nbsp;→ console-only log line  
* `yield from ah.run("pytest", capture="t")` → convenience helpers (see below)

Helper wrappers (`log`, `run`, `code`, `include`, `chat`, `ask`, `search`,
`spawn`) are re-exported as **`aider.helpers`** for easy import inside macros.
"""

from __future__ import annotations

import inspect
import shlex
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Generator, Optional

# ============================================================================ #
# Helper API – importable as `import aider.helpers as ah`                      #
# ============================================================================ #

def log(text: str) -> str:
    """Write a line to the console only (never sent to the LLM)."""
    return f"# {text}"

def chat(prompt: str) -> str:
    """Send a plain user message to the main model (equivalent to typing it)."""
    return f"> {prompt}"

def ask(prompt: str) -> str:
    """Shortcut for Aider’s `/ask …`."""
    return f"/ask {prompt}"

def search(query: str, *, max_results: int = 5, model_suffix=":online") -> str:
    """
    Switch temporarily to an online-capable model, ask *query*, then restore.
    Returns one multi-line action that /macro will execute step-by-step.
    """
    set_online   = f"/model +{model_suffix}"
    restore_prev = "/model -"
    ask_line     = f"> {query}"
    return "\n".join([set_online, ask_line, restore_prev])

def run(cmd: str, *, capture: Optional[str] = None
        ) -> Generator[str, str | None, str | None]:
    """Yield a shell command; optionally capture its output into a register."""
    suffix = f" >{capture}" if capture else ""
    result = yield f"! {cmd}{suffix}"
    return result

def code(fname: str, prompt: str
         ) -> Generator[str, str | None, str | None]:
    """Edit *fname* with the given prompt (wrapper for `/code …`)."""
    safe = prompt.replace("}", "\\}")
    result = yield f"/code {fname} {{{safe}}}"
    return result

def include(register: str) -> str:
    """Insert the contents of a register into the chat."""
    return f"/include {register}"

# --- async helper ----------------------------------------------------------- #
_EXEC       = ThreadPoolExecutor(max_workers=8)
_SPAWN_CMDS = None  # set when MacroRunner starts

def _run_action_silent(commands, action: str):
    """Run one macro action with console output suppressed."""
    io, orig = commands.io, commands.io.tool_output
    commands.io.tool_output = lambda *a, **kw: None
    try:
        return _dispatch_action(commands, action)
    finally:
        commands.io.tool_output = orig

def spawn(action: str):
    """Run *action* asynchronously, keep UI silent, return a future."""
    return _EXEC.submit(_run_action_silent, _SPAWN_CMDS, action)

# ============================================================================ #
# Internal utilities                                                           #
# ============================================================================ #

def _maybe_num(v: str) -> int | float | str:
    """Cast CLI values to int/float when possible."""
    if v.lstrip("-").isdigit():
        return int(v)
    try:
        return float(v)
    except ValueError:
        return v

def _parse_argline(argline: str) -> tuple[str, Dict[str, Any]]:
    """Split ‘module_path k=v …’ into (path, {k: v, …})."""
    parts  = shlex.split(argline)
    if not parts:
        raise ValueError("Usage: /macro <module> [key=value …]")
    mod    = parts[0]
    kwargs: Dict[str, Any] = {}
    for tok in parts[1:]:
        if "=" not in tok:
            raise ValueError(f"Bad arg '{tok}', expected key=value")
        k, v = tok.split("=", 1)
        kwargs[k] = _maybe_num(v)
    return mod, kwargs

def _import_module(spec: str):
    """Import by dotted name or absolute/relative *.py path."""
    if spec.endswith(".py") or Path(spec).expanduser().exists():
        path  = Path(spec).expanduser().resolve()
        name  = path.stem + "_macro"
        loader = types.ModuleType(name)
        with path.open("r", encoding="utf-8") as fh:
            code = fh.read()
        exec(compile(code, str(path), "exec"), loader.__dict__)
        sys.modules[name] = loader
        return loader
    return __import__(spec, fromlist=["*"])

def _dispatch_action(commands, action: str):
    """Execute one yielded action and return the result to the generator."""
    if action.startswith(("/", "!")):
        return commands.run(action)
    if action.startswith("# "):                    # console log
        commands.io.tool_output(action[2:])
        return None
    if action.startswith(">"):                    # user → LLM prompt
        return commands.coder.run(action[1:].lstrip())
    return commands.run(action)                   # fallback

# ============================================================================ #
# MacroRunner                                                                  #
# ============================================================================ #

class MacroRunner:
    """
    Thin wrapper so `Commands.cmd_macro()` only has to do::

        MacroRunner(io, coder.run).run(argline)
    """

    def __init__(self, io, run_fn):
        self.io     = io
        self._run   = run_fn  # function to execute /!/> actions

    def run(self, argline: str, **_ignored):
        global _SPAWN_CMDS
        commands = _ignored.get("commands") or self   # for spawn helper
        _SPAWN_CMDS = commands

        try:
            mod_spec, kwargs = _parse_argline(argline)
        except ValueError as err:
            self.io.tool_error(str(err))
            return

        try:
            module = _import_module(mod_spec)
        except Exception as err:
            self.io.tool_error(f"Import failed: {err}")
            return

        main = getattr(module, "main", None)
        if not (callable(main) and inspect.isgeneratorfunction(main)):
            self.io.tool_error("Macro must define a *generator* main(ctx, **kwargs)")
            return

        ctx = {
            "vars":       kwargs.copy(),
            "registers":  {},
            "counters":   {},
            "exit_code":  0,
            "coder":      _ignored.get("coder"),
            "io":         self.io,
            "send":       self._run,
        }

        gen = main(ctx, **kwargs)  # type: ignore[arg-type]

        try:
            action = next(gen)  # prime
            while True:
                result  = _dispatch_action(commands, action)
                action  = gen.send(result)
        except StopIteration:
            pass
        except Exception as err:
            self.io.tool_error(f"Macro runtime error: {err}")

# ============================================================================ #
# Re-export helpers as `aider.helpers`                                         #
# ============================================================================ #

_helpers = types.ModuleType("aider.helpers")
for _name in ("log", "run", "code", "include", "chat", "ask",
              "search", "spawn"):
    setattr(_helpers, _name, globals()[_name])
sys.modules["aider.helpers"] = _helpers

