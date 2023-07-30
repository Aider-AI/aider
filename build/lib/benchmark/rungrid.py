#!/usr/bin/env python

import subprocess
import sys

from aider.dump import dump  # noqa: F401


def main():
    models = [
        # "gpt-3.5-turbo-0301",
        "gpt-3.5-turbo-0613",
        # "gpt-3.5-turbo-16k-0613",
        # "gpt-4-0314",
        # "gpt-4-0613",
    ]
    edit_formats = [
        # "diff",
        # "diff-func",
        "whole",
        # "whole-func",
    ]

    for repeat in range(1, 10, 1):
        for model in models:
            for edit_format in edit_formats:
                # dump(model, edit_format)

                if "-func" in edit_format and "-03" in model:
                    continue

                # if (model, edit_format) == ("gpt-3.5-turbo-16k-0613", "whole-func"):
                #    # sublist reliably hangs the API?
                #    continue

                # dirname = f"rungrid-{model}-{edit_format}"
                dirname = f"rungrid-{model}-{edit_format}-repeat-{repeat}"
                run(dirname, model, edit_format)


def run(dirname, model, edit_format):
    cmd = [
        "./benchmark/benchmark.py",
        dirname,
        "--model",
        model,
        "--edit-format",
        edit_format,
        "--threads",
        "10",
        "--cont",
    ]
    print(" ".join(cmd))

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    status = main()
    sys.exit(status)
