from unittest import TestCase, mock

from aider.history import ChatSummary
from aider.models import Model


class TestChatSummary(TestCase):
    def setUp(self):
        self.mock_model = mock.Mock(spec=Model)
        self.mock_model.name = "gpt-3.5-turbo"
        self.mock_model.token_count = lambda msg: len(msg["content"].split())
        self.mock_model.info = {"max_input_tokens": 4096}
        self.mock_model.simple_send_with_retries = mock.Mock()
        self.chat_summary = ChatSummary(self.mock_model, max_tokens=100)

    def test_initialization(self):
        self.assertIsInstance(self.chat_summary, ChatSummary)
        self.assertEqual(self.chat_summary.max_tokens, 100)

    def test_too_big(self):
        messages = [
            {"role": "user", "content": "This is a short message"},
            {"role": "assistant", "content": "This is also a short message"},
        ]
        self.assertFalse(self.chat_summary.too_big(messages))

        long_message = {"role": "user", "content": " ".join(["word"] * 101)}
        self.assertTrue(self.chat_summary.too_big([long_message]))

    def test_tokenize(self):
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there"},
        ]
        tokenized = self.chat_summary.tokenize(messages)
        self.assertEqual(tokenized, [(2, messages[0]), (2, messages[1])])

    def test_summarize_all(self):
        self.mock_model.simple_send_with_retries.return_value = "This is a summary"
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there"},
        ]
        summary = self.chat_summary.summarize_all(messages)
        self.assertEqual(
            summary,
            [
                {
                    "role": "user",
                    "content": (
                        "I spoke to you previously about a number of things.\nThis is a summary"
                    ),
                }
            ],
        )

    def test_summarize(self):
        messages = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        messages.extend([{"role": "assistant", "content": f"Response {i}"} for i in range(10)])

        with mock.patch.object(
            self.chat_summary,
            "summarize_all",
            return_value=[{"role": "user", "content": "Summary"}],
        ):
            result = self.chat_summary.summarize(messages)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertLessEqual(len(result), len(messages))

    def test_fallback_to_second_model(self):
        mock_model1 = mock.Mock(spec=Model)
        mock_model1.name = "gpt-4"
        mock_model1.simple_send_with_retries = mock.Mock(side_effect=Exception("Model 1 failed"))
        mock_model1.info = {"max_input_tokens": 4096}
        mock_model1.token_count = lambda msg: len(msg["content"].split())

        mock_model2 = mock.Mock(spec=Model)
        mock_model2.name = "gpt-3.5-turbo"
        mock_model2.simple_send_with_retries = mock.Mock(return_value="Summary from Model 2")
        mock_model2.info = {"max_input_tokens": 4096}
        mock_model2.token_count = lambda msg: len(msg["content"].split())

        chat_summary = ChatSummary([mock_model1, mock_model2], max_tokens=100)

        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there"},
        ]

        summary = chat_summary.summarize_all(messages)

        # Check that both models were tried
        mock_model1.simple_send_with_retries.assert_called_once()
        mock_model2.simple_send_with_retries.assert_called_once()

        # Check that we got a summary from the second model
        self.assertEqual(
            summary,
            [
                {
                    "role": "user",
                    "content": (
                        "I spoke to you previously about a number of things.\nSummary from Model 2"
                    ),
                }
            ],
        )
