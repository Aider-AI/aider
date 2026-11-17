# AGENTS.md

Entry point for AI agents (and humans acting like one) working in this repository.
Read this file first. Then read `docs/ARCHITECTURE.md` before changing core code.

Aider is a terminal AI pair-programming tool: a Python package (`aider/`) that sends
repo context to an LLM, parses the LLM's edits, applies them to local files, and
commits them to git. Users run it on their own code, so every change here affects
real users' files and git history.

## 1. Where things are

| Path | What it is |
|---|---|
| `aider/main.py` | CLI entry (`aider = aider.main:main`). Parses args, builds the model and the coder, starts the loop. |
| `aider/coders/` | One class per edit format plus `base_coder.py` (the core loop). Registry: `aider/coders/__init__.py`. |
| `aider/models.py` | Model settings, aliases (`MODEL_ALIASES`), metadata, sanity checks. |
| `aider/resources/` | `model-settings.yml` and `model-metadata.json`: model data shipped with the package. |
| `aider/commands.py` | In-chat slash commands (`/add`, `/undo`, `/test`, ...). |
| `aider/repo.py`, `aider/repomap.py` | Git wrapper and the repo map (tree-sitter based). |
| `aider/queries/` | Tree-sitter query files used by the repo map. |
| `aider/io.py` | Terminal input and output. New user-facing output goes through `io` (`tool_output`, `tool_error`). Several modules still call `print()`; do not add more. |
| `tests/` | pytest suite. Configured by `pytest.ini`. (`aider/tests` does not exist.) |
| `benchmark/` | Benchmark harness. It runs LLM-generated code. See the Docker rule below. |
| `requirements/` | Dependency sources (`*.in`) and compiled lock files (`*.txt`). |
| `scripts/` | Release and maintenance scripts. Some are not meant for routine work. |
| `aider/website/` | The public docs site (Jekyll). User-facing docs live in `aider/website/docs/`. |

## 2. Commands (taken from config and CI, not from memory)

```bash
# Dev install (pyproject.toml defines the "dev" extra)
python -m venv ../aider_venv && source ../aider_venv/bin/activate
pip install -e .[dev]

# Tests (pytest.ini sets testpaths and AIDER_ANALYTICS=false)
pytest                               # full suite
pytest tests/basic/test_coder.py     # one file
pytest tests/basic/test_coder.py::TestCoder::test_specific_case

# Lint and format (.pre-commit-config.yaml, .flake8)
pre-commit run --all-files           # isort, black (line 100), flake8, codespell

# Smoke checks that need no API key
python -m aider --version
python -m aider --help
```

CI (`.github/workflows/ubuntu-tests.yml`) runs `pytest` on Python 3.10 to 3.14.
Windows and Docker builds also run in CI.

## 3. Guardrails (hard rules)

1. **Do not hand-edit generated files.** `requirements.txt`,
   `requirements/*.txt` and `aider/_version.py` are generated. To add a dependency,
   edit the matching `requirements/*.in`, then run `./scripts/pip-compile.sh`.
2. **Keep Python 3.10 to 3.14 compatible** (`pyproject.toml` `requires-python`).
   Do not use syntax or stdlib APIs newer than 3.10.
3. **No new type hints.** `CONTRIBUTING.md` says the project does not use them. A few
   existing annotations are exceptions. Do not add more, and do not reformat them.
4. **Tests never call a real LLM or need real keys.** Mock the model or the network.
   Tests must pass with `AIDER_ANALYTICS=false`, which `pytest.ini` sets.
5. **Never commit secrets.** `.aider*` is gitignored. Do not add `.env` files,
   API keys or credentials to tracked files.
6. **Benchmark code runs model-generated Python.** Run it only inside the Docker
   container described in `benchmark/README.md`. Never run it on the host.
7. **Do not edit `HISTORY.md` or bump versions by hand.** Releases use
   `scripts/versionbump.py`, which requires the `main` branch and a clean tree.
8. **Edits to user repos are auto-committed by design.** Preserve the `/undo`
   path and the commit-before-lint behaviour in `base_coder.py` unless the task says
   otherwise. Changing them is a behaviour change, so it needs tests and a stated reason.
9. **Keep the user-facing contract.** Flags, slash commands and edit formats are
   public. Renaming or removing one needs a deprecation path (`aider/deprecated.py`
   exists for this) and a docs update.
10. **Stay in your lane on docs.** `aider/website/_posts/` and `HISTORY.md` are
    historical records. Do not rewrite them to match current facts.

## 4. Adding things (extension points)

- **New edit format:** create `aider/coders/<name>_coder.py` with a unique
  `edit_format` string, register it in `aider/coders/__init__.py`, and add tests
  in `tests/basic/`. Check that `Coder.create` finds it (see `base_coder.py`).
- **New model alias or settings:** update `MODEL_ALIASES` in `aider/models.py` and
  `aider/resources/model-settings.yml`. Check the alias with `aider --list-models`.
- **New in-chat command:** add `cmd_<name>` to `aider/commands.py`, then add a test
  in `tests/basic/test_commands.py`.
- **New repo-map language:** add a query under `aider/queries/`. See
  `aider/repomap.py`.

## 5. Definition of done: what counts as evidence

Passing a check is one level of evidence. Do not claim a higher level than you reached.

| Level | What it proves | How to get it |
|---|---|---|
| L0 Compiles | Syntax is valid | `python -m compileall -q aider tests` |
| L1 Unit tests pass | The changed logic does what the tests check | `pytest` on the affected files, then the full suite |
| L2 Lint clean | Style and common errors | `pre-commit run --all-files` |
| L3 Operationally validated | The real CLI works for a user | Run `aider` on a scratch git repo with a real or local model, and record the commands and output |

L1 does not imply L3. If you could only reach L0 or L1 (for example, no API key or
no network), say so in your report and list what remains unverified.

When you report a result, include the exact command, its exit code and the relevant output.

## 6. Known gaps (read before trusting the docs)

These were found by checking docs against code. They are not fixed yet:

- Several docs still recommend "Claude 3.7 Sonnet" or "Claude 3.5 Sonnet". The `sonnet`
  alias now points to a newer model (`aider/models.py`). Check the alias, not the prose.
- Python versions are inconsistent across docs. The source of truth is `pyproject.toml`
  (3.10 to 3.14) and the CI matrix.
- `CONTRIBUTING.md` says tests are in `aider/tests` and that `requirements-dev.txt` is at
  the root. The correct paths are `tests/` and `requirements/requirements-dev.txt`.
- The README token badge (`15B tokens/week`) is a constant in `scripts/homepage.py`,
  not a measured value.

## 7. Where to read more

- `docs/ARCHITECTURE.md`: request flow, state, failure modes.
- `CONTRIBUTING.md`: PR process and the licence agreement.
- `benchmark/README.md`: how to measure model performance reproducibly.
