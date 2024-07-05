import unittest
from unittest.mock import patch, MagicMock
from aider.help import Help

class TestHelp(unittest.TestCase):
    @patch('aider.help.get_index')
    def setUp(self, mock_get_index):
        self.mock_index = MagicMock()
        mock_get_index.return_value = self.mock_index
        self.help = Help()

    def test_init(self):
        self.assertIsNotNone(self.help.retriever)

    def test_ask_with_mock(self):
        mock_node = MagicMock()
        mock_node.text = "Test content"
        mock_node.metadata = {"url": "https://example.com"}
        self.help.retriever.retrieve.return_value = [mock_node]

        result = self.help.ask("Test question")

        self.assertIn("# Question: Test question", result)
        self.assertIn('<doc from_url="https://example.com">', result)
        self.assertIn("Test content", result)
        self.assertIn("</doc>", result)

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
