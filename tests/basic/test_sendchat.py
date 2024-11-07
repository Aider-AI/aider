import unittest
from unittest.mock import MagicMock, patch


from aider.exceptions import LiteLLMExceptions
from aider.llm import litellm
from aider.sendchat import simple_send_with_retries


class PrintCalled(Exception):
    pass


class TestSendChat(unittest.TestCase):
    def test_litellm_exceptions(self):
        litellm_ex = LiteLLMExceptions()
        litellm_ex._load(strict=True)

    @patch("litellm.completion")
    @patch("builtins.print")
    def test_simple_send_with_retries_rate_limit_error(self, mock_print, mock_completion):
        mock = MagicMock()
        mock.status_code = 500

        # Set up the mock to raise
        mock_completion.side_effect = [
            litellm.RateLimitError(
                "rate limit exceeded",
                response=mock,
                llm_provider="llm_provider",
                model="model",
            ),
            None,
        ]

        # Call the simple_send_with_retries method
        simple_send_with_retries("model", ["message"])
        assert mock_print.call_count == 3
