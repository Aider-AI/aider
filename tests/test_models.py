import unittest

from aider.models import Model


class TestModels(unittest.TestCase):
    def test_max_context_tokens(self):
        model = Model("gpt-3.5-turbo", validate_environment=False)
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = Model("gpt-3.5-turbo-16k", validate_environment=False)
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = Model("gpt-3.5-turbo-1106", validate_environment=False)
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = Model("gpt-4", validate_environment=False)
        self.assertEqual(model.info["max_input_tokens"], 8 * 1024)

        model = Model("gpt-4-32k", validate_environment=False)
        self.assertEqual(model.info["max_input_tokens"], 32 * 1024)

        model = Model("gpt-4-0613", validate_environment=False)
        self.assertEqual(model.info["max_input_tokens"], 8 * 1024)


if __name__ == "__main__":
    unittest.main()
