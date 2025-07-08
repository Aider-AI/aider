# flake8: noqa: E501

import unittest

from benchmark import cleanup_test_output


class TestCleanupTestOutput(unittest.TestCase):
    def test_cleanup_test_output(self):
        # Test case with timing info
        output = "Ran 5 tests in 0.003s\nOK"
        expected = "\nOK"
        self.assertEqual(cleanup_test_output(output), expected)

        # Test case without timing info
        output = "OK"
        expected = "OK"
        self.assertEqual(cleanup_test_output(output), expected)

    def test_cleanup_test_output_lines(self):
        # Test case with timing info
        output = """F
======================================================================
FAIL: test_cleanup_test_output (test_benchmark.TestCleanupTestOutput.test_cleanup_test_output)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/gauthier/Projects/aider/benchmark/test_benchmark.py", line 14, in test_cleanup_test_output
    self.assertEqual(cleanup_test_output(output), expected)
AssertionError: 'OK' != 'OKx'
- OK
+ OKx
?   +
"""

        expected = """F
====
FAIL: test_cleanup_test_output (test_benchmark.TestCleanupTestOutput.test_cleanup_test_output)
----
Traceback (most recent call last):
  File "/Users/gauthier/Projects/aider/benchmark/test_benchmark.py", line 14, in test_cleanup_test_output
    self.assertEqual(cleanup_test_output(output), expected)
AssertionError: 'OK' != 'OKx'
- OK
+ OKx
?   +
"""
        self.assertEqual(cleanup_test_output(output), expected)
