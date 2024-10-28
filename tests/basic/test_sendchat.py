import unittest
from unittest.mock import MagicMock, patch

import httpx

from aider.llm import litellm
from aider.sendchat import retry_exceptions, simple_send_with_retries

# ai: fix these test errors! it should not test for 2 print() calls!
FAILED tests/basic/test_sendchat.py::TestSendChat::test_simple_send_with_retries_connection_error - AssertionError: Expected 'print' to have been called once. Called 2 times.
FAILED tests/basic/test_sendchat.py::TestSendChat::test_simple_send_with_retries_rate_limit_error - AssertionError: Expected 'print' to have been called once. Called 2 times.

class PrintCalled(Exception):
    pass


class TestSendChat(unittest.TestCase):
    def test_retry_exceptions(self):
        """Test that retry_exceptions() can be called without raising errors"""
        retry_exceptions()  # Should not raise any exceptions

    @patch("litellm.completion")
    @patch("builtins.print")
    def test_simple_send_with_retries_rate_limit_error(self, mock_print, mock_completion):
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

        # Call the simple_send_with_retries method
        simple_send_with_retries("model", ["message"])
        mock_print.assert_called_once()

    @patch("litellm.completion")
    @patch("builtins.print")
    def test_simple_send_with_retries_connection_error(self, mock_print, mock_completion):
        # Set up the mock to raise
        mock_completion.side_effect = [
            httpx.ConnectError("Connection error"),
            None,
        ]

        # Call the simple_send_with_retries method
        simple_send_with_retries("model", ["message"])
        mock_print.assert_called_once()
