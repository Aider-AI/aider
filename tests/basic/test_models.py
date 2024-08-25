import unittest
from unittest.mock import patch, mock_open
import json
import time
from pathlib import Path

from aider.models import Model, get_model_info


class TestModels(unittest.TestCase):
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

    @patch('aider.models.litellm._lazy_module', False)
    @patch('aider.models.Path.home')
    @patch('aider.models.Path.stat')
    @patch('aider.models.safe_read_json')
    @patch('aider.models.safe_write_json')
    @patch('aider.models.requests.get')
    def test_get_model_info(self, mock_get, mock_write_json, mock_read_json, mock_stat, mock_home):
        # Setup
        mock_home.return_value = Path('/mock/home')
        mock_stat.return_value.st_mtime = time.time() - 86400 * 2  # 2 days old

        # Test case 1: Cache exists and is fresh
        mock_read_json.return_value = {'test_model': {'info': 'cached'}}
        mock_stat.return_value.st_mtime = time.time() - 3600  # 1 hour old
        self.assertEqual(get_model_info('test_model'), {'info': 'cached'})

        # Test case 2: Cache doesn't exist or is old, GitHub fetch succeeds
        mock_read_json.return_value = None
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'test_model': {'info': 'from_github'}}
        self.assertEqual(get_model_info('test_model'), {'info': 'from_github'})

        # Test case 3: Cache doesn't exist, GitHub fetch fails, fallback to local resource
        mock_get.return_value.status_code = 404
        with patch('importlib.resources.open_text') as mock_open_text:
            mock_open_text.return_value.__enter__.return_value.read.return_value = json.dumps({'test_model': {'info': 'local_backup'}})
            self.assertEqual(get_model_info('test_model'), {'info': 'local_backup'})

        # Test case 4: All previous methods fail, fallback to litellm.get_model_info
        mock_open_text.side_effect = Exception("Resource not found")
        with patch('aider.models.litellm.get_model_info') as mock_litellm_get_model_info:
            mock_litellm_get_model_info.return_value = {'info': 'from_litellm'}
            self.assertEqual(get_model_info('test_model'), {'info': 'from_litellm'})

        # Test case 5: Everything fails
        mock_litellm_get_model_info.side_effect = Exception("LiteLLM failed")
        self.assertEqual(get_model_info('test_model'), {})


if __name__ == "__main__":
    unittest.main()
