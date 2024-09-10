import unittest
from unittest.mock import patch, MagicMock
from aider.models import Model
from aider.coders import Coder

class TestBosEosIntegration(unittest.TestCase):
    @patch("aider.sendchat.send_completion")
    def test_send_completion_integration(self, mock_send_completion):
        model = Model("gpt-4", bos_token="<BOS>", eos_token="<EOS>")
        coder = Coder.create(main_model=model)

        # Mock the necessary methods and attributes
        coder.io = MagicMock()
        coder.partial_response_content = ""
        coder.partial_response_function_call = {}

        # Simulate sending a message
        coder.send(messages=[{"role": "user", "content": "Hello"}])

        # Print debug information
        print(f"mock_send_completion.call_count: {mock_send_completion.call_count}")
        print(f"mock_send_completion.call_args: {mock_send_completion.call_args}")

        # Check if send_completion was called with correct BOS and EOS tokens
        mock_send_completion.assert_called_once()
        _, kwargs = mock_send_completion.call_args
        self.assertEqual(kwargs.get("bos_token"), "<BOS>")
        self.assertEqual(kwargs.get("eos_token"), "<EOS>")

if __name__ == "__main__":
    unittest.main()
