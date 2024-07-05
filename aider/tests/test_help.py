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

    def test_ask(self):
        mock_node = MagicMock()
        mock_node.text = "Test content"
        mock_node.metadata = {"url": "https://example.com"}
        self.help.retriever.retrieve.return_value = [mock_node]

        result = self.help.ask("Test question")

        self.assertIn("# Question: Test question", result)
        self.assertIn('<doc from_url="https://example.com">', result)
        self.assertIn("Test content", result)
        self.assertIn("</doc>", result)


if __name__ == '__main__':
    unittest.main()
