#!/usr/bin/env bash

# if there's a run-tests.sh in the project, use that instead
if [ -f run-tests.sh ]; then
    exec ./run-tests.sh
fi

errors=0

if [ -f pyproject.toml ]; then
    # This looks like a Python package.
    VIRTUAL_ENV=
    uv sync --quiet --all-groups --all-extras
    UV_PYTHON=.venv

    # Run pytest if it's available.
    if uv pip show --quiet pytest; then
        uv run pytest || errors=$?
    fi
fi

if [ -f Cargo.toml ]; then
    cargo test || errors=$?
fi

exit $errors
