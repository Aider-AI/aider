import os
from unittest import TestCase, mock

from aider.commands import Commands
from aider.io import InputOutput
from aider.search import CONTEXT_SEARCH_URL, search_web


class TestWebSearch(TestCase):
    def test_search_web_formats_context_results(self):
        response = mock.MagicMock()
        response.json.return_value = {
            "results": [
                {
                    "url": "https://example.com/docs",
                    "title": "Example docs",
                    "description": "Current API documentation.",
                    "relevance": "high",
                }
            ]
        }
        client = mock.MagicMock()
        client.post.return_value = response

        with mock.patch("aider.search.httpx.Client") as client_class:
            client_class.return_value.__enter__.return_value = client
            result = search_web("example API", "secret")

        client_class.assert_called_once_with(timeout=30, verify=True)
        client.post.assert_called_once_with(
            CONTEXT_SEARCH_URL,
            headers={"Authorization": "Bearer secret"},
            json={"query": "example API", "numResults": 10},
        )
        self.assertEqual(
            result,
            (
                "- [Example docs](https://example.com/docs) (high relevance)\n"
                "  Current API documentation."
            ),
        )

    def test_cmd_search_adds_results_to_chat(self):
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = mock.MagicMock()
        coder.cur_messages = []
        commands = Commands(io, coder)

        with (
            mock.patch.dict(os.environ, {"CONTEXT_DEV_API_KEY": "secret"}),
            mock.patch("aider.commands.search_web", return_value="- Result"),
        ):
            commands.cmd_search("latest Python release")

        self.assertIn("latest Python release", coder.cur_messages[0]["content"])
        self.assertIn("- Result", coder.cur_messages[0]["content"])
        self.assertEqual(coder.cur_messages[1], {"role": "assistant", "content": "Ok."})

    def test_cmd_search_requires_api_key(self):
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        commands = Commands(io, mock.MagicMock())

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(io, "tool_error") as tool_error,
        ):
            commands.cmd_search("latest Python release")

        tool_error.assert_called_once_with(
            "Please set CONTEXT_DEV_API_KEY or use --api-key context_dev=<key>."
        )
