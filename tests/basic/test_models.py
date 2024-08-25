import unittest
from unittest.mock import patch
import json
from pathlib import Path

from aider.models import Model, get_model_info


class TestModels(unittest.TestCase):
    @patch('aider.models.Path.home')
    @patch('aider.models.time.time')
    @patch('aider.models.Path.stat')
    @patch('aider.models.Path.read_text')
    def test_get_model_info_cached(self, mock_read_text, mock_stat, mock_time, mock_home):
        # Setup mock
        mock_home.return_value = Path('/mock/home')
        mock_time.return_value = 1000000
        mock_stat.return_value.st_mtime = 999999  # File modified 1 second ago
        mock_read_text.return_value = json.dumps({"gpt-3.5-turbo": {"max_input_tokens": 16385}})

        # Test
        info = get_model_info("gpt-3.5-turbo")
        self.assertEqual(info, {"max_input_tokens": 16385})

    @patch('aider.models.Path.home')
    @patch('aider.models.time.time')
    @patch('aider.models.Path.stat')
    @patch('aider.models.requests.get')
    def test_get_model_info_fetch(self, mock_get, mock_stat, mock_time, mock_home):
        # Setup mock
        mock_home.return_value = Path('/mock/home')
        mock_time.return_value = 1000000
        mock_stat.return_value.st_mtime = 900000  # File modified a long time ago
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"gpt-4": {"max_input_tokens": 8192}}

        # Test
        info = get_model_info("gpt-4")
        self.assertEqual(info, {"max_input_tokens": 8192})

    @patch('aider.models.Path.home')
    @patch('aider.models.time.time')
    @patch('aider.models.Path.stat')
    @patch('aider.models.requests.get')
    @patch('aider.models.litellm.get_model_info')
    def test_get_model_info_fallback(self, mock_litellm, mock_get, mock_stat, mock_time, mock_home):
        # Setup mock
        mock_home.return_value = Path('/mock/home')
        mock_time.return_value = 1000000
        mock_stat.return_value.st_mtime = 900000  # File modified a long time ago
        mock_get.return_value.status_code = 404  # Simulate failed request
        mock_litellm.return_value = {"max_input_tokens": 4096}

        # Test
        info = get_model_info("unknown-model")
        self.assertEqual(info, {"max_input_tokens": 4096})

    def test_get_model_info_nonexistent(self):
        info = get_model_info("non-existent-model")
        self.assertEqual(info, {})
    def test_max_context_tokens(self):
        model = Model("gpt-3.5-turbo")
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = Model("gpt-3.5-turbo-16k")
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = Model("gpt-3.5-turbo-1106")
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = Model("gpt-4")
        self.assertEqual(model.info["max_input_tokens"], 8 * 1024)

        model = Model("gpt-4-32k")
        self.assertEqual(model.info["max_input_tokens"], 32 * 1024)

        model = Model("gpt-4-0613")
        self.assertEqual(model.info["max_input_tokens"], 8 * 1024)


if __name__ == "__main__":
    unittest.main()
