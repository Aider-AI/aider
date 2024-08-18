.PHONY: all format help

all: help

# Define variables for Python files and Git commands
PYTHON_FILES=.
MYPY_CACHE=.mypy_cache
CHANGED_FILES := $(shell git diff --name-only --diff-filter=ACMRT HEAD | grep '\.py$$')

lint format: PYTHON_FILES=.
lint_package: PYTHON_FILES=aider

format:
	@if [ -n "$(CHANGED_FILES)" ]; then \
		echo "Formatting changed files:"; \
		echo "$(CHANGED_FILES)" | tr ' ' '\n'; \
		black -l 100 $(CHANGED_FILES); \
	else \
		echo "No Python files have been modified."; \
	fi

format-all:
	black -l 100 $(PYTHON_FILES)

######################
# HELP
######################

help:
	@echo '----'
	@echo 'format                       - run code formatters on changed files'
	@echo 'format-all                   - run code formatters on all files'