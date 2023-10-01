import unittest
from aider.command_completions import CommandCompletions

class TestCommandCompletions(unittest.TestCase):
    def setUp(self):
        class MockCoder:
            def get_all_relative_files(self):
                return ['a/b/c/d', 'a/b/c/e', 'a/b/c/f', 'aa/bb/cc/dd']

            def get_inchat_relative_files(self):
                return []

        self.coder = MockCoder()
        self.command_completions = CommandCompletions(self.coder)

    def test_completions_add(self):
        partial = "ab/c"
        result = sorted([completion.text for completion in self.command_completions.completions_add(partial)])
        expected = ['a/b/c/d', 'a/b/c/e', 'a/b/c/f', 'aa/bb/cc/dd']
        self.assertEqual(result, expected)

        partial = "aabb"
        result = sorted([completion.text for completion in self.command_completions.completions_add(partial)])
        expected = ['aa/bb/cc/dd']
        self.assertEqual(result, expected)

    def test_completions_drop(self):
        partial = "a/b"
        result = list(self.command_completions.completions_drop(partial))
        expected = []
        self.assertEqual(result, expected)
