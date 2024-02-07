import unittest
from unittest.mock import MagicMock

from aider.models import Model, OpenRouterModel


class TestModels(unittest.TestCase):
    def test_max_context_tokens(self):
        model = Model.create("gpt-3.5-turbo")
        self.assertEqual(model.max_context_tokens, 4 * 1024)

        model = Model.create("gpt-3.5-turbo-16k")
        self.assertEqual(model.max_context_tokens, 16385)

        model = Model.create("gpt-3.5-turbo-1106")
        self.assertEqual(model.max_context_tokens, 16385)

        model = Model.create("gpt-4")
        self.assertEqual(model.max_context_tokens, 8 * 1024)

        model = Model.create("gpt-4-32k")
        self.assertEqual(model.max_context_tokens, 32 * 1024)

        model = Model.create("gpt-4-0613")
        self.assertEqual(model.max_context_tokens, 8 * 1024)

    def test_openrouter_model_properties(self):
        client = MagicMock()

        class ModelData:
            def __init__(self, id, object, context_length, pricing):
                self.id = id
                self.object = object
                self.context_length = context_length
                self.pricing = pricing

        model_data = ModelData(
            "openai/gpt-4", "model", "8192", {"prompt": "0.00006", "completion": "0.00012"}
        )

        class ModelList:
            def __init__(self, data):
                self.data = data

        client.models.list.return_value = ModelList([model_data])

        model = OpenRouterModel(client, "gpt-4")
        self.assertEqual(model.name, "openai/gpt-4")
        self.assertEqual(model.max_context_tokens, 8192)
        self.assertEqual(model.prompt_price, 0.06)
        self.assertEqual(model.completion_price, 0.12)


if __name__ == "__main__":
    unittest.main()
