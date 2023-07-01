#!/usr/bin/env python

import sys

from aider.dump import dump
from benchmark import main as benchmark_main


def main():
    models = [
        "gpt-3.5-turbo-0301",
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
    ]
    edit_formats = [
        "diff",
        "diff-func",
        "whole",
        "whole-func",
    ]

    for model in models:
        for edit_format in edit_formats:
            # dump(model, edit_format)
            dirname = f"/benchmarks/rungrid-{model}-{edit_format}"
            dump(dirname)

            benchmark_main(
                dirnames=[dirname],
                model=model,
                edit_format=edit_format,
                threads=10,
                cont=True,
            )


if __name__ == "__main__":
    status = main()
    sys.exit(status)
