#!/usr/bin/env python

"""Applies a blocklist to requirements files."""

import fileinput
from pathlib import Path
import re
import sys

from packaging.requirements import Requirement

PROJECT_ROOT = Path(__file__).parent.parent.absolute()
BLOCKLIST_PATH = PROJECT_ROOT / "requirements/blocklist.in"


def is_requirement(line):
    """Returns True if the line is an actual requirement."""

    def empty():
        return not line.strip()

    def comment():
        return re.match(r"^\s*#", line)

    return not empty() and not comment()


def parse_blocklist():
    """Parses a list of blocked requirements."""
    with open(BLOCKLIST_PATH, encoding="utf-8") as file:
        for line in file:
            if is_requirement(line):
                yield line.strip()


def parse_requirements():
    """Parses the requirement file(s) given as an input."""
    for line in fileinput.input(encoding="utf-8"):
        if is_requirement(line):
            yield Requirement(line)


def filtered_requirements_lines():
    """Parses the requirement file(s) given as an input.
    Filters out all sections that represent a blocked requirement.
    """
    include_section = True
    blocked_requirements = set(parse_blocklist())

    for line in fileinput.input(encoding="utf-8"):
        if is_requirement(line):
            name = Requirement(line).name
            include_section = name not in blocked_requirements
            if not include_section:
                print(f"Removing blocked requirement: {name}", file=sys.stderr)
        if include_section:
            yield line


def main():
    """Applies the blocklist to the requirements file(s) given as
    an input. Removes blocked requirements.
    """
    for line in filtered_requirements_lines():
        print(line, end="")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # play nice with Unix pipelines
        pass
