import unittest
from unittest.mock import patch, MagicMock
from aider.main import main
from aider.models import Model
from aider.coders import Coder


class TestBosEosIntegration(unittest.TestCase):
    @patch("aider.main.Coder.create")
    @patch("aider.main.Model")
    def test_bos_eos_integration(self, mock_model, mock_coder_create):
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance
        mock_coder_instance = MagicMock()
        mock_coder_create.return_value = mock_coder_instance

        # Simulate command-line arguments
        test_args = ["--bos-token", "<BOS>", "--eos-token", "<EOS>", "--model", "gpt-4", "--no-git"]
        
        with patch("sys.argv", ["aider"] + test_args):
            main()

        # Check if Model was initialized with correct BOS and EOS tokens
        mock_model.assert_called_once_with("gpt-4", weak_model=None, bos_token="<BOS>", eos_token="<EOS>")

        # Check if Coder.create was called with the correct model
        mock_coder_create.assert_called_once()
        _, kwargs = mock_coder_create.call_args
        self.assertEqual(kwargs["main_model"], mock_model_instance)

    @patch("aider.sendchat.send_completion")
    def test_send_completion_integration(self, mock_send_completion):
        model = Model("gpt-4", bos_token="<BOS>", eos_token="<EOS>")
        coder = Coder.create(main_model=model)

        # Simulate sending a message
        coder.send(messages=[{"role": "user", "content": "Hello"}])

        # Check if send_completion was called with correct BOS and EOS tokens
        mock_send_completion.assert_called_once()
        _, kwargs = mock_send_completion.call_args
        self.assertEqual(kwargs["bos_token"], "<BOS>")
        self.assertEqual(kwargs["eos_token"], "<EOS>")


if __name__ == "__main__":
    unittest.main()
