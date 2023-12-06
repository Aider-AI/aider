import unittest
from unittest.mock import MagicMock, patch

import httpx
import openai

from aider.sendchat import send_with_retries


class PrintCalled(Exception):
    pass


class TestSendChat(unittest.TestCase):
    @patch("builtins.print")
    def test_send_with_retries_rate_limit_error(self, mock_print):
        mock_client = MagicMock()

        # Set up the mock to raise
        mock_client.chat.completions.create.side_effect = [
            openai.RateLimitError(
                "rate limit exceeded",
                response=MagicMock(),
                body=None,
            ),
            None,
        ]

        # Call the send_with_retries method
        send_with_retries(mock_client, "model", ["message"], None, False)
        mock_print.assert_called_once()

    @patch("aider.sendchat.openai.ChatCompletion.create")
    @patch("builtins.print")
    def test_send_with_retries_connection_error(self, mock_print, mock_chat_completion_create):
        mock_client = MagicMock()

        # Set up the mock to raise
        mock_client.chat.completions.create.side_effect = [
            httpx.ConnectError("Connection error"),
            None,
        ]

        # Call the send_with_retries method
        send_with_retries(mock_client, "model", ["message"], None, False)
        mock_print.assert_called_once()
