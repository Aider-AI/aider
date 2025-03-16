import unittest
from aider.main import parse_lint_cmds
from aider.io import InputOutput

class TestParseLintCmds(unittest.TestCase):
    def setUp(self):
        self.io = InputOutput(pretty=False)

    def test_parse_lint_cmds(self):
        lint_cmds = ["python: flake8 --select=E9"]
        expected = {"python": "flake8 --select=E9 --bind 127.0.0.1"}
        result = parse_lint_cmds(lint_cmds, self.io)
        self.assertEqual(result, expected)

    def test_parse_lint_cmds_no_lang(self):
        lint_cmds = ["flake8 --select=E9"]
        expected = {None: "flake8 --select=E9 --bind 127.0.0.1"}
        result = parse_lint_cmds(lint_cmds, self.io)
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main()