import unittest
from unittest.mock import patch, MagicMock
from aider.help import Help

class TestHelp(unittest.TestCase):

    def setUp(self):
        self.help = Help()

    def test_init(self):
        self.assertIsNotNone(self.help.retriever)

    def test_ask_without_mock(self):
        help_instance = Help()
        question = "What is aider?"
        result = help_instance.ask(question)

        self.assertIn(f"# Question: {question}", result)
        self.assertIn("<doc", result)
        self.assertIn("</doc>", result)
        self.assertGreater(len(result), 100)  # Ensure we got a substantial response

        # Check for some expected content (adjust based on your actual help content)
        self.assertIn("aider", result.lower())
        self.assertIn("ai", result.lower())
        self.assertIn("chat", result.lower())

if __name__ == '__main__':
    unittest.main()
