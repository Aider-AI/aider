# Task: Add node-secure and python-api-secure to the starter catalog

## Acceptance Criteria
1. `task starters:validate` passes with no errors
2. `task starters:prove -- --starter node-secure` completes successfully
3. `task starters:prove -- --starter python-api-secure` completes successfully
4. `task starters:verify` passes for all starters (existing three plus both new entries)
5. `task ci` passes in the repository root

## Context
- All task commands must run inside the maintainer container (see AGENTS.md)
- The catalog lives at `starters/catalog.toml` — schema_version = 1
- Three entries already exist: `python-secure`, `python-node-secure`, `java-secure` — use these as the reference pattern
- Templates already exist at `templates/node-secure/` and `templates/python-api-secure/`
- `task starters:prove` generates the starter into a temp directory, runs `task init` inside it, then runs each `proof_commands` entry and checks each `proof_paths` file exists
- `proof_paths` must list exactly the files present after generation + `task init` — no more, no less

## Workflow
1. **Survey** — read `starters/catalog.toml` and `templates/python-secure/` end-to-end to internalise the pattern before writing anything
2. **Survey node-secure** — read `templates/node-secure/Taskfile.yml` and `.devcontainer/` to identify: task contract commands, what `task init` produces, what `task ci` requires
3. **Add node-secure entry** to `starters/catalog.toml`:
   - language: `"node"`
   - source_template: `"templates/node-secure"`
   - proof_commands: `["task ci"]`
   - proof_paths: derive from what exists after `task init` (check pnpm-lock.yaml, node_modules, .artifacts if any)
   - features: `["security-baseline", "node-engineering", "agent-runtime"]`
4. Run `task starters:validate` — fix any schema errors before proceeding
5. Run `task starters:prove -- --starter node-secure` — read failures carefully; adjust proof_paths or fix template issues until it passes
6. **Survey python-api-secure** — read `templates/python-api-secure/Taskfile.yml` to understand its task contract; it uses uv and has more tasks than the base python-secure starter
7. **Add python-api-secure entry** to `starters/catalog.toml`:
   - language: `"python"`
   - source_template: `"templates/python-api-secure"`
   - proof_commands: `["task ci"]`
   - proof_paths: derive from what exists after `task init`
   - features: `["security-baseline", "python-engineering", "agent-runtime"]`
8. Run `task starters:prove -- --starter python-api-secure` — iterate until it passes
9. Run `task starters:verify` — this validates the catalog then proves all five starters; fix any regressions in existing starters
10. Run `task ci` from the repository root — fix any failures
11. Commit each working starter as a separate commit with message format: `feat(starters): add <name> catalog entry and proof`

## Constraints
- Always do: run `task starters:validate` after every catalog edit; commit each new entry once its prove passes; run `task lint` before committing
- Ask first: any changes to the content of `templates/` files; any changes to the three existing catalog entries; adding new dependencies to the maintainer image
- Never do: weaken existing proof_paths (removing required files); skip `task ci` before committing; modify `starters/catalog.toml` schema_version

## If you get stuck
- `task starters:show -- --starter <name>` prints the resolved catalog entry as JSON — use this to verify your entry was parsed correctly
- If `task starters:prove` fails on a proof_path, run `find <generated-dir> -type f` to see what actually exists after generation
- If a task inside the generated starter fails, cd into the generated directory and run `task ci` manually to see the full output
