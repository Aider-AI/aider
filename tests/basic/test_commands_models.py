from types import SimpleNamespace
from unittest import TestCase, mock

from aider.commands import Commands
from aider.io import InputOutput


class TestCommandsModels(TestCase):
    def test_cmd_models_handles_import_error(self):
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        commands = Commands(io, SimpleNamespace())

        with (
            mock.patch(
                "aider.commands.models.print_matching_models",
                side_effect=ImportError("cannot import name '_parsing' from 'openai.lib'"),
            ),
            mock.patch.object(io, "tool_error") as mock_tool_error,
        ):
            commands.cmd_models("gpt")

        mock_tool_error.assert_called_once()
        message = mock_tool_error.call_args.args[0]
        self.assertIn("Unable to load model metadata for /models", message)
        self.assertIn("cannot import name '_parsing' from 'openai.lib'", message)
