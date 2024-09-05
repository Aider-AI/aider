#!/usr/bin/env python

import argparse
import os
import sys
from pathlib import Path

import pathspec

from .dump import dump  # noqa: F401
from .grep_ast import TreeContext
from .parsers import PARSERS


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("pattern", nargs="?", help="the pattern to search for")
    parser.add_argument("filenames", nargs="*", help="the files to display", default=".")
    parser.add_argument("--encoding", default="utf8", help="file encoding")
    parser.add_argument("--languages", action="store_true", help="show supported languages")
    parser.add_argument("-i", "--ignore-case", action="store_true", help="ignore case distinctions")
    parser.add_argument("--color", action="store_true", help="force color printing", default=None)
    parser.add_argument(
        "--no-color", action="store_false", help="disable color printing", dest="color"
    )
    parser.add_argument("--no-gitignore", action="store_true", help="ignore .gitignore file")
    parser.add_argument("--verbose", action="store_true", help="enable verbose output")
    parser.add_argument("-n", "--line-number", action="store_true", help="display line numbers")
    args = parser.parse_args()

    # If stdout is not a terminal, set color to False
    if args.color is None:
        args.color = os.isatty(1)

    # If --languages is provided, print the parsers table and exit
    if args.languages:
        for ext, lang in sorted(PARSERS.items()):
            print(f"{ext}: {lang}")
        return
    elif not args.pattern:
        print("Please provide a pattern to search for")
        return 1

    gitignore = None
    if not args.no_gitignore:
        for parent in Path("./xxx").resolve().parents:
            potential_gitignore = parent / ".gitignore"
            if potential_gitignore.exists():
                gitignore = potential_gitignore
                break

    if gitignore:
        with gitignore.open() as f:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", f)
    else:
        spec = pathspec.PathSpec.from_lines("gitwildmatch", [])

    for fname in enumerate_files(args.filenames, spec):
        process_filename(fname, args)


def enumerate_files(fnames, spec, use_spec=False):
    for fname in fnames:
        fname = Path(fname)

        # oddly, Path('.').name == "" so we will recurse it
        if fname.name.startswith(".") or use_spec and spec.match_file(fname):
            continue

        if fname.is_file():
            yield str(fname)
            continue

        if fname.is_dir():
            for sub_fnames in enumerate_files(fname.iterdir(), spec, True):
                yield sub_fnames


def process_filename(filename, args):
    try:
        with open(filename, "r", encoding=args.encoding) as file:
            code = file.read()
    except UnicodeDecodeError:
        return

    try:
        tc = TreeContext(
            filename, code, color=args.color, verbose=args.verbose, line_number=args.line_number
        )
    except ValueError:
        return

    loi = tc.grep(args.pattern, args.ignore_case)
    if not loi:
        return

    tc.add_lines_of_interest(loi)
    tc.add_context()

    print()
    print(f"{filename}:")

    print(tc.format(), end="")

    print()


if __name__ == "__main__":
    res = main()
    sys.exit(res)
