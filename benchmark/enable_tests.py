#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


def enable_javascript_tests(content):
    replacements = {
        "xtest": "test",
        "test.skip": "test",
        "xit": "it",
        "it.skip": "it",
    }

    pattern = re.compile(
        r"^(?P<indent>[ \t]*)(?P<name>xtest|test\.skip|xit|it\.skip)(?=\s*\()",
        re.MULTILINE,
    )
    return pattern.sub(
        lambda match: match.group("indent") + replacements[match.group("name")], content
    )


def enable_java_tests(content):
    return re.sub(
        r"^[ \t]*@Disabled(?:\([^\r\n]*\))?[ \t]*\r?\n",
        "",
        content,
        flags=re.MULTILINE,
    )


def enable_tests(path):
    content = path.read_text()
    if path.suffix == ".js":
        updated = enable_javascript_tests(content)
    elif path.suffix == ".java":
        updated = enable_java_tests(content)
    else:
        raise ValueError(f"Unsupported test file: {path}")

    if updated != content:
        path.write_text(updated)


def main():
    parser = argparse.ArgumentParser(description="Enable skipped benchmark tests")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    for path in args.paths:
        enable_tests(path)


if __name__ == "__main__":
    main()
