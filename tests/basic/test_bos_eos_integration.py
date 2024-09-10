import unittest
from unittest.mock import MagicMock, patch

from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput

class TestBosEosIntegration(unittest.TestCase):
    def setUp(self):
        self.model = Model("gpt-4", bos_token="<BOS>", eos_token="<EOS>")

    @patch("aider.coders.base_coder.send_completion")
    def test_send_completion_integration(self, mock_send_completion):
        io = InputOutput(yes=True)
        coder = Coder.create(self.model, None, io=io)

        def mock_send(*args, **kwargs):
            coder.partial_response_content = "Test response"
            coder.partial_response_function_call = {}
            return []

        coder.send = mock_send

        # Simulate running the coder
        coder.run(with_message="Hello")

        # Check if send_completion was called with correct BOS and EOS tokens
        mock_send_completion.assert_called()
        _, kwargs = mock_send_completion.call_args
        self.assertEqual(kwargs.get("bos_token"), "<BOS>")
        self.assertEqual(kwargs.get("eos_token"), "<EOS>")

    def test_model_initialization(self):
        self.assertEqual(self.model.bos_token, "<BOS>")
        self.assertEqual(self.model.eos_token, "<EOS>")

    @patch("aider.coders.base_coder.send_completion")
    def test_coder_creation_with_bos_eos(self, mock_send_completion):
        io = InputOutput(yes=True)
        coder = Coder.create(self.model, None, io=io)
        
        self.assertEqual(coder.main_model.bos_token, "<BOS>")
        self.assertEqual(coder.main_model.eos_token, "<EOS>")

    @patch("aider.coders.base_coder.send_completion")
    def test_coder_send_with_bos_eos(self, mock_send_completion):
        io = InputOutput(yes=True)
        coder = Coder.create(self.model, None, io=io)

        mock_send_completion.return_value = ({"role": "assistant", "content": "Test response"}, None)

        coder.send(messages=[{"role": "user", "content": "Hello"}])

        mock_send_completion.assert_called_once()
        _, kwargs = mock_send_completion.call_args
        self.assertEqual(kwargs.get("bos_token"), "<BOS>")
        self.assertEqual(kwargs.get("eos_token"), "<EOS>")

if __name__ == "__main__":
    unittest.main()
