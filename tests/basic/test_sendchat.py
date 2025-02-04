import unittest
from unittest.mock import MagicMock, patch

from aider.exceptions import LiteLLMExceptions
from aider.llm import litellm
from aider.models import Model


class PrintCalled(Exception):
    pass


class TestSendChat(unittest.TestCase):
    def setUp(self):
        self.mock_messages = [{"role": "user", "content": "Hello"}]
        self.mock_model = "gpt-4"

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
        Model(self.mock_model).simple_send_with_retries(self.mock_messages)
        assert mock_print.call_count == 3

    @patch("litellm.completion")
    def test_send_completion_basic(self, mock_completion):
        # Setup mock response
        mock_response = MagicMock()
        mock_completion.return_value = mock_response

        # Test basic send_completion
        hash_obj, response = Model(self.mock_model).send_completion(
            self.mock_messages, functions=None, stream=False
        )

        assert response == mock_response
        mock_completion.assert_called_once()

    @patch("litellm.completion")
    def test_send_completion_with_functions(self, mock_completion):
        mock_function = {"name": "test_function", "parameters": {"type": "object"}}

        hash_obj, response = Model(self.mock_model).send_completion(
            self.mock_messages, functions=[mock_function], stream=False
        )

        # Verify function was properly included in tools
        called_kwargs = mock_completion.call_args.kwargs
        assert "tools" in called_kwargs
        assert called_kwargs["tools"][0]["function"] == mock_function

    @patch("litellm.completion")
    def test_simple_send_attribute_error(self, mock_completion):
        # Setup mock to raise AttributeError
        mock_completion.return_value = MagicMock()
        mock_completion.return_value.choices = None

        # Should return None on AttributeError
        result = Model(self.mock_model).simple_send_with_retries(self.mock_messages)
        assert result is None

    @patch("litellm.completion")
    @patch("builtins.print")
    def test_simple_send_non_retryable_error(self, mock_print, mock_completion):
        # Test with an error that shouldn't trigger retries
        mock = MagicMock()
        mock.status_code = 400

        mock_completion.side_effect = litellm.NotFoundError(
            message="Invalid request", llm_provider="test_provider", model="test_model"
        )

        result = Model(self.mock_model).simple_send_with_retries(self.mock_messages)
        assert result is None
        # Should only print the error message
        assert mock_print.call_count == 1

    def test_ensure_alternating_roles_empty(self):
        from aider.sendchat import ensure_alternating_roles

        messages = []
        result = ensure_alternating_roles(messages)
        assert result == []

    def test_ensure_alternating_roles_single_message(self):
        from aider.sendchat import ensure_alternating_roles

        messages = [{"role": "user", "content": "Hello"}]
        result = ensure_alternating_roles(messages)
        assert result == messages

    def test_ensure_alternating_roles_already_alternating(self):
        from aider.sendchat import ensure_alternating_roles

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]
        result = ensure_alternating_roles(messages)
        assert result == messages

    def test_ensure_alternating_roles_consecutive_user(self):
        from aider.sendchat import ensure_alternating_roles

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "Are you there?"},
        ]
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "Are you there?"},
        ]
        result = ensure_alternating_roles(messages)
        assert result == expected

    def test_ensure_alternating_roles_consecutive_assistant(self):
        from aider.sendchat import ensure_alternating_roles

        messages = [
            {"role": "assistant", "content": "Hi there"},
            {"role": "assistant", "content": "How can I help?"},
        ]
        expected = [
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "How can I help?"},
        ]
        result = ensure_alternating_roles(messages)
        assert result == expected

    def test_ensure_alternating_roles_mixed_sequence(self):
        from aider.sendchat import ensure_alternating_roles

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "Are you there?"},
            {"role": "assistant", "content": "Yes"},
            {"role": "assistant", "content": "How can I help?"},
            {"role": "user", "content": "Write code"},
        ]
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "Are you there?"},
            {"role": "assistant", "content": "Yes"},
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "How can I help?"},
            {"role": "user", "content": "Write code"},
        ]
        result = ensure_alternating_roles(messages)
        assert result == expected
