import unittest
from benchmark.benchmark import cleanup_test_output

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
