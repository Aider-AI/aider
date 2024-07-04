import unittest
from unittest.mock import MagicMock, patch

import httpx

from aider.llm import litellm
from aider.sendchat import send_with_retries


class PrintCalled(Exception):
    pass


class TestSendChat(unittest.TestCase):
    @patch("litellm.completion")
    @patch("builtins.print")
    def test_send_with_retries_rate_limit_error(self, mock_print, mock_completion):
        mock = MagicMock()
        mock.status_code = 500

        # Set up the mock to raise
        mock_completion.side_effect = [
            litellm.exceptions.RateLimitError(
                "rate limit exceeded",
                response=mock,
                llm_provider="llm_provider",
                model="model",
            ),
            None,
        ]

        # Call the send_with_retries method
        send_with_retries("model", ["message"], None, False)
        mock_print.assert_called_once()

    @patch("litellm.completion")
    @patch("builtins.print")
    def test_send_with_retries_connection_error(self, mock_print, mock_completion):
        # Set up the mock to raise
        mock_completion.side_effect = [
            httpx.ConnectError("Connection error"),
            None,
        ]

        # Call the send_with_retries method
        send_with_retries("model", ["message"], None, False)
        mock_print.assert_called_once()
