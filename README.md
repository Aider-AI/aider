## 🧩 What’s new in the `nbardy/aider` fork — **Macro Pipelines**

This fork adds a **first‑class macro system** so you can script repeatable,
agent‑like workflows *inside* Aider—without writing a separate shell wrapper
or learning a new DSL.

### Key points

| Feature | How it works |
|---------|--------------|
| **`/macro` command** | ` /macro my_macro.py [arg=value …] ` loads a Python module and runs its `main()` generator in‑process. |
| **Generator API** | `main(ctx, **kwargs)` yields strings (e.g. `/run …`, `/code …`, or plain prompts). After each yield the macro receives the captured output via `.send(result)`, making two‑way loops trivial. |
| **Helper library** | `aider_helpers.log / run / code / include` hide slash‑command syntax so macro code stays clean. |
| **No subprocess spin‑up** | Macros execute inside Aider’s interpreter—fast and stateful. |
| **Opt‑in security** | Macros are disabled by default. Enable with `--enable‑macros` *or* add `macros: enabled` in `~/.aider.conf.yml`. An optional `macro.allowlist` file restricts which modules may run. |
| **Logs on disk** | Every macro step is still echoed to chat *and* written to `./agent-logs/`, which is `.gitignore`‑d by default. |

### Quick start

```bash
# 1. install this fork
pip install git+https://github.com/nbardy/aider.git@main

# 2. enable macros (one‑off flag or config file)
aider --enable-macros scene.json


Below is a drop‑in **“Examples”** section you can append to your fork’s `README.md` (or splice into an existing examples table). It showcases the three flagship macros shipped in `examples/`:


## 🔍 Macro Examples

These macros live in **`examples/`**.  
Run them inside an Aider session (started with `--enable‑macros`) using  
`/macro <file.py> [arg=value …]`.

| Macro | What it does | Typical command |
|-------|--------------|-----------------|
| **`render_loop_program.py`** | Renders → *Judge YES/NO* → Critique + Patch → repeat ≤ 10× until the judge outputs **YES**. | `/macro examples/render_loop_program.py req="Render a knight on a bridge at sunset"` |
| **`ideate_explore_solve.py`** | Generates an idea pool, clusters & critiques, synthesises a plan, drafts code/answer, then asks Aider to polish it. | `/macro examples/ideate_explore_solve.py goal="Design a minimal REST API for todo items"` |
| **`pytest_fix_until_green.py`** | Runs `pytest`, captures failures, asks Aider to auto‑patch code, and loops until tests pass or max attempts reached. | `/macro examples/pytest_fix_until_green.py max_tries=8` |

---

### 1 · `render_loop_program.py` — visual QA loop

```python
import aider_helpers as ah

def main(ctx, req, scene_file="scene.json", max_tries=10):
    crit = req if "\n" in req else open(req).read() if os.path.exists(req) else req
    for i in range(1, max_tries + 1):
        ver = yield from ah.code(scene_file,
            f"Judge against CRITERIA below.\n**CRITERIA:**\n{crit}\n\nYES or NO?")
        if ver.strip().upper().startswith("YES"):
            yield ah.log(f"✅ YES at attempt {i}!"); return
        critique = yield from ah.code(scene_file,
            "You said NO. List mismatches and give a patch.")
        yield from ah.code(scene_file, f"Apply this patch:\n{critique}")
    yield ah.log("🚫 Max attempts reached without success.")
```

---

### 2 · `ideate_explore_solve.py` — brainstorm → plan → solution

```python
import aider_helpers as ah

def main(ctx, goal, idea_target=10):
    ideas = []
    while len(ideas) < idea_target:
        idea = yield "> 💡 Emit an idea for: " + goal
        ideas.append(idea.strip())
    yield ah.log("🧮 Clustering ideas …")
    clusters = yield from ah.code("scratch.md", "Cluster the ideas:\n" + "\n".join(ideas))
    plan = yield from ah.code("PLAN.md", "Write a step‑by‑step plan based on clusters above.")
    solution = yield from ah.code("SOLUTION.md", f"Implement the plan:\n{plan}")
    polished = yield from ah.code("SOLUTION.md", "Critique & polish the solution for production readiness.")
    yield ah.log("🎉 Ideate‑explore‑solve loop completed.")
```

---

### 3 · `pytest_fix_until_green.py` — red‑>green test loop

```python
import aider_helpers as ah

def main(ctx, max_tries=10):
    for i in range(1, max_tries + 1):
        out = yield from ah.run("pytest -q", capture="t_out")
        if ctx["exit_code"] == 0:
            yield ah.log(f"✅ Tests passed on try {i}")
            return
        yield "/include t_out"
        yield from ah.code("{Fix failing tests using t_out above}")
    yield ah.log("🚫 Could not fix tests after max tries.")
```

---

> **Tip:** keep `examples/` on your Python path so macros can import shared helpers:
>
> ```bash
> export PYTHONPATH=$PYTHONPATH:$(pwd)/examples
> ```

These scripts demonstrate how **simple generator functions + `aider_helpers`** let you build reusable, agent‑like workflows entirely in Python—no new DSL required.
