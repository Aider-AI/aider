# Architecture

This document describes how aider works internally, for people and agents who change
the core. It is based on the code as it is now. Where a detail could change, it points
to the file that holds the truth.

## 1. Big picture

```
 user shell
    │  aider [flags] [files]
    ▼
 main.py ── args.py (config files, env, CLI flags)
    │
    ├─ git: find root, sanity check, optional gitignore update   (repo.py)
    ├─ model: pick model, validate keys, load settings           (models.py, resources/)
    ├─ Coder.create(edit_format=...)  ── picks one class         (coders/)
    ▼
 Coder.run() ── loop over user messages (io.py: prompt input)
    │
    ├─ run_one(): preprocess input, handle /commands            (commands.py)
    ├─ send_message(): build prompt (repo map, files, history)  (base_coder.py, repomap.py)
    │      └─ llm call via litellm (lazy import)                 (llm.py, sendchat.py)
    ├─ get_edits(): parse the LLM reply in the coder's format
    ├─ apply_updates(): write edited files                       (search_replace.py, editblock_*, udiff_*, ...)
    ├─ auto_commit(): git commit the edits                       (repo.py)
    ├─ lint_edited(): run linters, feed errors back if any       (linter.py)
    ├─ run_shell_commands(): user-approved shell commands         (run_cmd.py)
    └─ test cmd (optional): feed failures back                    (commands.py cmd_test)
```

The core loop is in `aider/coders/base_coder.py`: `run()`, `run_one()`,
`send_message()`, `apply_updates()`, `auto_commit()`, `lint_edited()`.

## 2. Components

| Component | Files | Responsibility | Invariant |
|---|---|---|---|
| CLI and setup | `main.py`, `args.py`, `args_formatter.py`, `onboarding.py` | Build the run from flags, config files and env. | Config precedence is defined in `args.py`. Do not invent a new one. |
| Coders | `coders/*.py` | One class per edit format: the prompt, the reply parser and the applier. | Each `edit_format` string is unique and registered in `coders/__init__.py`. |
| Models | `models.py`, `resources/model-settings.yml`, `resources/model-metadata.json`, `openrouter.py` | Aliases, context window, edit format defaults, capability flags. | The `sonnet`-style aliases are the user API. Changing what an alias points to is a user-visible change. |
| LLM access | `llm.py`, `sendchat.py` | Wraps litellm. `llm.py` imports litellm lazily to keep startup fast. | Messages must alternate roles (`ensure_alternating_roles`). |
| Git | `repo.py` | Read tracked files, commit, undo, ignore rules. | Aider only commits the files it edited. |
| Repo map | `repomap.py`, `queries/` | Ranked summary of symbols across the repo, sent as context. | Bounded by `map_tokens` (default 1024). |
| Commands | `commands.py` | In-chat `/` commands. | Each command is `cmd_<name>`. |
| Terminal I/O | `io.py`, `mdstream.py`, `waiting.py` | User-facing output, prompts, confirmations. | New output goes through `io`. Some older modules still use `print()`. |
| Lint and test | `linter.py`, `run_cmd.py` | Run user-configured lint and test commands. | Commands run only from user config or explicit user input. |
| Watch mode | `watch.py`, `watch_prompts.py` | Reacts to comments ending in `AI!` (change request) or `AI?` (question). | Only comments with those markers start a request. |
| Analytics | `analytics.py`, `versioncheck.py` | Opt-in telemetry and version checks. | Off in tests (`AIDER_ANALYTICS=false`). Users can disable it. |

## 3. Extension points

- **Edit format:** subclass `Coder`, set `edit_format`, implement the parser and applier.
  Register the class in `coders/__init__.py`. See `architect_coder.py` for a coder that
  delegates to another coder.
- **Model:** add an entry to `resources/model-settings.yml`. Add an alias to
  `MODEL_ALIASES` if users need a short name.
- **Command:** add `cmd_<name>` to `Commands`.
- **Language in repo map:** add tree-sitter queries under `queries/`.

## 4. State and where it lives

| State | Location | Notes |
|---|---|---|
| User's code and git history | User's repo | Aider writes edits and commits here. |
| Chat history | `.aider.chat.history.md` in the repo (default) | Gitignored by `.aider*`. |
| Input history | `.aider.input.history` | Same. |
| Home-directory state | `~/.aider/` (`/app/.aider` in Docker, because the image sets `HOME=/app`) | Holds analytics and similar state. |
| Analytics id | `~/.aider/analytics.json` | Opt-in. |
| Repo map tags cache | `.aider.tags.cache.v<N>/` in the repo (`repomap.py`, `TAGS_CACHE_DIR`). Falls back to memory if the disk cache fails. | Gitignored by `.aider*`. Deleting it only costs a rebuild. |

## 5. Failure modes and recovery

| Failure | Where it is raised | What the user sees | Recovery |
|---|---|---|---|
| Unknown edit format | `base_coder.py` (`UnknownEditFormat`) | Error at startup | Pick a format from the listed valid ones. |
| No API key for the model | `base_coder.py` (`MissingAPIKeyError`) | Error naming the key | Set the key (see `docs/config/api-keys.md`). |
| LLM stops at token limit | `FinishReasonLength` | Warning, partial reply | Use a smaller set of files or a model with a larger context. |
| Malformed edit in reply | Edit parsers in `coders/` | Error, reflection asks the LLM to retry | Retry. Track the rate in benchmarks. |
| Bad edit applied | Git | Changes committed | `/undo` reverts the last aider commit. |
| Lint errors after edit | `lint_edited()` | Errors fed back to the LLM | Fix or `/undo`. |
| Repo not a git repo or dirty | `main.py` `sanity_check_repo` | Prompt or warning | Initialize git or commit first. |

Hard failures should stop before writing files. Anything that writes to user files must
either go through git (so `/undo` works) or ask first.

## 6. Test layout and what each level proves

- `tests/basic/`: unit and integration tests for core modules. Most of the coverage is here.
- `tests/help/`, `tests/browser/`, `tests/scrape/`: optional features. They need extra
  requirements (`requirements/requirements-help.txt`, `-browser.txt`, `-playwright.txt`).
- Passing tests show that the code matches the tests. They do not show that a user can
  run the tool end to end. For that, see the L3 level in `AGENTS.md`.

## 7. Benchmarks

`benchmark/benchmark.py` runs aider on the Exercism polyglot exercises and records pass
rates. Results are reproducible when the record includes the model, edit format and
commit hash, and the run was not dirty. See `benchmark/README.md`. The harness runs
model-generated code, so it runs only inside Docker.

## 8. Known architectural risks

- `base_coder.py` is large and holds most of the loop. Changes there have wide effects.
  Prefer adding a test before changing it.
- Model settings are split between `models.py` and the YAML and JSON resources. A new
  setting must be read in both places, and the tests should cover the lookup.
- The docs site and the code can drift (see `AGENTS.md` section 6). Treat docs as a
  claim that needs checking against the code.
