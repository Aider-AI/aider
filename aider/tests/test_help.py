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

    @patch('os.environ')
    @patch('aider.help.Settings')
    @patch('aider.help.HuggingFaceEmbedding')
    def test_environment_and_settings(self, mock_hf, mock_settings, mock_environ):
        Help()
        mock_environ.__setitem__.assert_called_with("TOKENIZERS_PARALLELISM", "true")
        self.assertEqual(mock_settings.embed_model, mock_hf.return_value)
        mock_hf.assert_called_with(model_name="BAAI/bge-small-en-v1.5")

if __name__ == '__main__':
    unittest.main()
