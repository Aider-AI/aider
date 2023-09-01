import unittest
from unittest.mock import patch

from aider.models import Model, OpenRouterModel


class TestModels(unittest.TestCase):
    def test_max_context_tokens(self):
        model = Model.create("gpt-3.5-turbo")
        self.assertEqual(model.max_context_tokens, 4 * 1024)

        model = Model.create("gpt-3.5-turbo-16k")
        self.assertEqual(model.max_context_tokens, 16 * 1024)

        model = Model.create("gpt-4")
        self.assertEqual(model.max_context_tokens, 8 * 1024)

        model = Model.create("gpt-4-32k")
        self.assertEqual(model.max_context_tokens, 32 * 1024)

        model = Model.create("gpt-4-0101")
        self.assertEqual(model.max_context_tokens, 8 * 1024)

        model = Model.create("gpt-4-32k-2123")
        self.assertEqual(model.max_context_tokens, 32 * 1024)

    @patch("openai.Model.list")
    def test_openrouter_model_properties(self, mock_model_list):
        import openai

        old_base = openai.api_base
        openai.api_base = "https://openrouter.ai/api/v1"
        mock_model_list.return_value = {
            "data": [
                {
                    "id": "openai/gpt-4",
                    "object": "model",
                    "context_length": "8192",
                    "pricing": {"prompt": "0.00006", "completion": "0.00012"},
                }
            ]
        }
        mock_model_list.return_value = type(
            "", (), {"data": mock_model_list.return_value["data"]}
        )()

        model = OpenRouterModel("gpt-4")
        self.assertEqual(model.name, "openai/gpt-4")
        self.assertEqual(model.max_context_tokens, 8192)
        self.assertEqual(model.prompt_price, 0.06)
        self.assertEqual(model.completion_price, 0.12)
        openai.api_base = old_base


if __name__ == "__main__":
    unittest.main()
