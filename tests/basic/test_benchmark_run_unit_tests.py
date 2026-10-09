"""Regression coverage for benchmark scoring when a test runner is silent."""

import ast
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load_runner():
    # The benchmark CLI imports optional dependencies that the main test suite does not install.
    source = Path(__file__).resolve().parents[2] / "benchmark" / "benchmark.py"
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"run_unit_tests", "cleanup_test_output"}
    ]
    namespace = {
        "Path": Path,
        "os": os,
        "re": re,
        "shutil": shutil,
        "subprocess": subprocess,
        "dump": lambda _: None,
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["run_unit_tests"]


class TestBenchmarkRunUnitTests(unittest.TestCase):
    def test_exit_status_is_not_lost_when_runner_output_is_empty(self):
        run_unit_tests = load_runner()
        with tempfile.TemporaryDirectory() as root:
            testdir = Path(root) / "exercise"
            testdir.mkdir()
            history = Path(root) / "history.md"

            cases = [
                (0, "", None),
                (1, "assertion failed", "assertion failed"),
                (1, "", "Tests failed with exit code 1"),
            ]
            for returncode, output, expected in cases:
                with self.subTest(returncode=returncode, output=output):
                    result = subprocess.CompletedProcess(["pytest"], returncode, output)
                    with patch.object(subprocess, "run", return_value=result):
                        errors = run_unit_tests(
                            Path(root) / "original",
                            testdir,
                            history,
                            ["test_sample.py"],
                        )
                    self.assertEqual(errors, expected)


if __name__ == "__main__":
    unittest.main()
