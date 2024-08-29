#!/usr/bin/env bash

# if there's a run-lint.sh in the project, use that instead
if [ -f run-lint.sh ]; then
    exec ./run-lint.sh
fi

errors=0

run() {
    local -n errors_ref=errors
    command -v uv >/dev/null || return
    uv pip show --quiet "$1" || return
    uv run $@ || errors_ref=$?
}

if [ -f pyproject.toml ]; then
    # This looks like a Python package.
    VIRTUAL_ENV=
    uv sync --quiet --all-groups --all-extras
    UV_PYTHON=.venv
    run darker
    run graylint
fi

for file in "$@"; do
    case "$file" in
        *.yml|*.yaml)
            uvx yamllint "$file" || errors=$?
            ;;
        *.sh|*.md|*.rst|*.txt)
            uvx codespell "$file" || errors=$?
            ;;
    esac
done

if [ -f Cargo.toml ]; then
  rustfmt --edition=2021 "$@" || errors=$?
  run cargo clippy || errors=$?
fi

if git ls-files "*.js" "*.mjs" "*.ts" 2>/dev/null | grep -q .; then
  if command -v eslint >/dev/null; then
    eslint "$@" || errors=$?
  fi
fi

find -name "*.nix" -exec nix-instantiate --parse {} \+ >/dev/null || errors=$?

exit $errors
