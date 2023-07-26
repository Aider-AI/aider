import unittest
from unittest.mock import patch

import openai
import requests

from aider.sendchat import send_with_retries


class TestSendChat(unittest.TestCase):
    @patch("aider.sendchat.openai.ChatCompletion.create")
    @patch("builtins.print")
    def test_send_with_retries_rate_limit_error(self, mock_print, mock_chat_completion_create):
        # Set up the mock to raise RateLimitError on
        # the first call and return None on the second call
        mock_chat_completion_create.side_effect = [
            openai.error.RateLimitError("Rate limit exceeded"),
            None,
        ]

        # Call the send_with_retries method
        send_with_retries("model", ["message"], None, False)

        # Assert that print was called once
        mock_print.assert_called_once()

    @patch("aider.sendchat.openai.ChatCompletion.create")
    @patch("builtins.print")
    def test_send_with_retries_connection_error(self, mock_print, mock_chat_completion_create):
        # Set up the mock to raise ConnectionError on the first call
        # and return None on the second call
        mock_chat_completion_create.side_effect = [
            requests.exceptions.ConnectionError("Connection error"),
            None,
        ]

        # Call the send_with_retries method
        send_with_retries("model", ["message"], None, False)

        # Assert that print was called once
        mock_print.assert_called_once()
