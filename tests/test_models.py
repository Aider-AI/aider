import unittest
from aider.models import Model

class TestModels(unittest.TestCase):
    def test_max_context_tokens(self):
        model = Model('gpt-3.5')
        self.assertEqual(model.max_context_tokens, 4*1024)

if __name__ == '__main__':
    unittest.main()
