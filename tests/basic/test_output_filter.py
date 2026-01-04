"""Tests for the output_filter module."""

import unittest

from aider.output_filter import (
    filter_output,
    is_error_line,
    is_noise_line,
    truncate_output,
)


class TestIsErrorLine(unittest.TestCase):
    def test_python_traceback(self):
        self.assertTrue(is_error_line("Traceback (most recent call last):"))
        self.assertTrue(is_error_line('  File "test.py", line 42'))
        self.assertTrue(is_error_line("ValueError: invalid value"))
        self.assertTrue(is_error_line("AssertionError"))

    def test_pytest_errors(self):
        self.assertTrue(is_error_line("FAILED tests/test_foo.py::test_bar"))
        self.assertTrue(is_error_line("E       assert 1 == 2"))

    def test_rust_errors(self):
        self.assertTrue(is_error_line("error[E0308]: mismatched types"))
        self.assertTrue(is_error_line("error: could not compile"))
        self.assertTrue(is_error_line("thread 'main' panicked at 'error'"))

    def test_go_errors(self):
        self.assertTrue(is_error_line("panic: runtime error"))
        self.assertTrue(is_error_line("--- FAIL: TestFoo (0.00s)"))
        self.assertTrue(is_error_line("    foo_test.go:42: expected 1, got 2"))

    def test_javascript_errors(self):
        self.assertTrue(is_error_line("Error: something went wrong"))
        self.assertTrue(is_error_line("    at Object.<anonymous> (test.js:1:1)"))
        self.assertTrue(is_error_line("  ✕ should do something"))
        self.assertTrue(is_error_line("FAIL src/test.js"))

    def test_java_errors(self):
        self.assertTrue(is_error_line("java.lang.NullPointerException:"))
        self.assertTrue(is_error_line("    at com.example.Test.run(Test.java:42)"))
        self.assertTrue(is_error_line("Caused by: java.io.IOException"))

    def test_generic_errors(self):
        self.assertTrue(is_error_line("[ERROR] Build failed"))
        self.assertTrue(is_error_line("FATAL: connection refused"))
        self.assertTrue(is_error_line("FAILURE: Build failed"))

    def test_non_error_lines(self):
        self.assertFalse(is_error_line("All tests passed"))
        self.assertFalse(is_error_line("Building project..."))
        self.assertFalse(is_error_line("OK (42 tests)"))


class TestIsNoiseLine(unittest.TestCase):
    def test_pip_noise(self):
        self.assertTrue(is_noise_line("Collecting requests"))
        self.assertTrue(is_noise_line("Downloading requests-2.28.0.tar.gz"))
        self.assertTrue(is_noise_line("Installing collected packages: requests"))
        self.assertTrue(is_noise_line("Requirement already satisfied: requests"))
        self.assertTrue(is_noise_line("Successfully installed requests-2.28.0"))

    def test_progress_bars(self):
        self.assertTrue(is_noise_line("  50%|█████     | 50/100"))

    def test_separators(self):
        self.assertTrue(is_noise_line("=" * 70))
        self.assertTrue(is_noise_line("-" * 40))

    def test_non_noise_lines(self):
        self.assertFalse(is_noise_line("Error: test failed"))
        self.assertFalse(is_noise_line("FAILED test_foo"))


class TestTruncateOutput(unittest.TestCase):
    def test_short_output_not_truncated(self):
        output = "line1\nline2\nline3"
        result, truncated = truncate_output(output, max_lines=10)
        self.assertEqual(result, output)
        self.assertFalse(truncated)

    def test_long_output_truncated(self):
        lines = [f"line{i}" for i in range(500)]
        output = "\n".join(lines)
        result, truncated = truncate_output(output, max_lines=200)
        self.assertTrue(truncated)
        self.assertIn("truncated", result)
        # Should be shorter than original
        self.assertLess(len(result.splitlines()), 500)

    def test_preserves_head_and_tail(self):
        lines = [f"line{i}" for i in range(500)]
        output = "\n".join(lines)
        result, truncated = truncate_output(
            output, max_lines=200, head_lines=50, tail_lines=100
        )
        result_lines = result.splitlines()
        # Head should be preserved
        self.assertEqual(result_lines[0], "line0")
        self.assertEqual(result_lines[49], "line49")
        # Tail should be preserved
        self.assertEqual(result_lines[-1], "line499")

    def test_extracts_error_lines(self):
        lines = ["normal"] * 100
        lines.append("Error: something went wrong")
        lines.extend(["normal"] * 100)
        lines.append("ValueError: bad value")
        lines.extend(["normal"] * 200)
        output = "\n".join(lines)

        result, truncated = truncate_output(output, max_lines=200)
        self.assertTrue(truncated)
        self.assertIn("Error: something went wrong", result)
        self.assertIn("error-related lines extracted", result)

    def test_empty_output(self):
        result, truncated = truncate_output("", max_lines=200)
        self.assertEqual(result, "")
        self.assertFalse(truncated)

    def test_none_output(self):
        result, truncated = truncate_output(None, max_lines=200)
        self.assertIsNone(result)
        self.assertFalse(truncated)


class TestFilterOutput(unittest.TestCase):
    def test_returns_dict_with_metadata(self):
        output = "line1\nline2\nline3"
        result = filter_output(output, max_lines=10)
        self.assertIn("output", result)
        self.assertIn("truncated", result)
        self.assertIn("original_lines", result)
        self.assertIn("final_lines", result)

    def test_short_output_metadata(self):
        output = "line1\nline2\nline3"
        result = filter_output(output, max_lines=10)
        self.assertEqual(result["output"], output)
        self.assertFalse(result["truncated"])
        self.assertEqual(result["original_lines"], 3)
        self.assertEqual(result["final_lines"], 3)

    def test_long_output_metadata(self):
        lines = [f"line{i}" for i in range(500)]
        output = "\n".join(lines)
        result = filter_output(output, max_lines=200)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["original_lines"], 500)
        self.assertLess(result["final_lines"], 500)

    def test_empty_output(self):
        result = filter_output("", max_lines=200)
        self.assertEqual(result["output"], "")
        self.assertFalse(result["truncated"])
        self.assertEqual(result["original_lines"], 0)
        self.assertEqual(result["final_lines"], 0)


if __name__ == "__main__":
    unittest.main()
