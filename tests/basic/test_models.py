import json
import unittest
from pathlib import Path
from unittest.mock import patch

from aider.models import Model, get_model_info


class TestModels(unittest.TestCase):
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
