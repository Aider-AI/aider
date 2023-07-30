import unittest

from aider.models import Model


class TestModels(unittest.TestCase):
    def test_max_context_tokens(self):
        model = Model("gpt-3.5-turbo")
        self.assertEqual(model.max_context_tokens, 4 * 1024)

        model = Model("gpt-3.5-turbo-16k")
        self.assertEqual(model.max_context_tokens, 16 * 1024)

        model = Model("gpt-4")
        self.assertEqual(model.max_context_tokens, 8 * 1024)

        model = Model("gpt-4-32k")
        self.assertEqual(model.max_context_tokens, 32 * 1024)

        model = Model("gpt-4-0101")
        self.assertEqual(model.max_context_tokens, 8 * 1024)

        model = Model("gpt-4-32k-2123")
        self.assertEqual(model.max_context_tokens, 32 * 1024)


if __name__ == "__main__":
    unittest.main()
