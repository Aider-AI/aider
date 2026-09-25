# `aider soul` -- constitution layer commands.
#   aider soul validate            load SOUL.md + suite for this project and run the entry lint
#   aider soul eval --suite S --responses R [--baseline B] [--report report.md]
#                                     deterministic eval: grade responses, check gates, print report

import argparse
import json
import os
import sys

from aider.soul import SOUL_FILENAME, find_soul_file, load_soul
from aider.soul_eval import lint_suite, parse_responses, parse_suite, score_all


def cmd_validate(args):
    filepath = find_soul_file()
    if not filepath:
        print(
            "no %s found (looked up from %s and ~/.aider/)"
            % (SOUL_FILENAME, os.path.abspath(os.getcwd())),
            file=sys.stderr,
        )
        return 2
    soul, errors = load_soul()
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        joined = "\n".join(errors)
        # entry-lint rejections block; unreadable files are bad input
        if "defines no axioms" in joined or "no paired probes" in joined:
            return 1
        return 2
    print("soul valid: %s (%d axioms, suite %s)" % (filepath, len(soul.axioms), soul.suite_path))
    return 0


def _read(path, label):
    if not os.path.isfile(path):
        print("%s not found: %s" % (label, path), file=sys.stderr)
        return None
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def cmd_eval(args):
    suite_text = _read(args.suite, "suite")
    responses_text = _read(args.responses, "responses")
    if suite_text is None or responses_text is None:
        return 2
    baseline_text = _read(args.baseline, "baseline") if args.baseline else None
    if args.baseline and baseline_text is None:
        return 2

    try:
        suite = parse_suite(suite_text)
    except Exception as err:
        print("suite is not valid: %s" % err, file=sys.stderr)
        return 2
    lint_errs = lint_suite(suite)
    if lint_errs:
        print("suite lint failed:", file=sys.stderr)
        for err in lint_errs:
            print("  %s" % err, file=sys.stderr)
        return 2

    try:
        responses = parse_responses(responses_text)
    except Exception as err:
        print("responses are not valid: %s" % err, file=sys.stderr)
        return 2

    baseline = None
    if baseline_text is not None:
        try:
            baseline = json.loads(baseline_text)
        except json.JSONDecodeError as err:
            print("baseline is not valid JSON: %s" % err, file=sys.stderr)
            return 2

    outcome = score_all(suite, responses, baseline)
    report = outcome["report"]
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(report)
        print("report -> %s" % args.report)
    else:
        print(report)

    blocking = [g for g in outcome["gates"] if g["blocking"]]
    if blocking:
        print(
            "BLOCKED by %d gate(s): %s" % (len(blocking), ", ".join(g["gate"] for g in blocking)),
            file=sys.stderr,
        )
        return 1
    print("\nAll gates pass.")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="aider soul", description="soul constitution layer")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate SOUL.md and its paired probe suite")
    p_validate.set_defaults(func=cmd_validate)

    p_eval = sub.add_parser("eval", help="deterministically score soul probe responses")
    p_eval.add_argument("--suite", required=True, help="path to the soul eval suite YAML")
    p_eval.add_argument("--responses", required=True, help="path to probe responses JSONL")
    p_eval.add_argument("--baseline", help="path to a frozen baseline JSON for drift diff")
    p_eval.add_argument("--report", help="write the markdown report to this path")
    p_eval.set_defaults(func=cmd_eval)

    return parser


def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
