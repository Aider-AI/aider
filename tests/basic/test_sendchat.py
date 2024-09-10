import unittest
from unittest.mock import MagicMock, patch

import httpx

from aider.llm import litellm
from aider.sendchat import simple_send_with_retries, send_completion


class PrintCalled(Exception):
    pass


class TestSendChat(unittest.TestCase):
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

    @patch("litellm.completion")
    def test_send_completion_with_bos_eos_tokens(self, mock_completion):
        model_name = "test-model"
        messages = [{"role": "user", "content": "Hello"}]
        functions = None
        stream = False
        bos_token = "<BOS>"
        eos_token = "<EOS>"

        send_completion(
            model_name,
            messages,
            functions,
            stream,
            bos_token=bos_token,
            eos_token=eos_token,
        )

        mock_completion.assert_called_once()
        kwargs = mock_completion.call_args[1]
        self.assertEqual(kwargs["bos_token"], "<BOS>")
        self.assertEqual(kwargs["eos_token"], "<EOS>")

    @patch("litellm.completion")
    def test_send_completion_without_bos_eos_tokens(self, mock_completion):
        model_name = "test-model"
        messages = [{"role": "user", "content": "Hello"}]
        functions = None
        stream = False

        send_completion(model_name, messages, functions, stream)

        mock_completion.assert_called_once()
        kwargs = mock_completion.call_args[1]
        self.assertNotIn("bos_token", kwargs)
        self.assertNotIn("eos_token", kwargs)
