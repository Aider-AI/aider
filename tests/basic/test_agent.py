import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import git

from aider.coders import Coder
from aider.commands import Commands, SwitchCoder
from aider.dump import dump  # noqa: F401
from aider.io import InputOutput
from aider.models import Model
from aider.utils import GitTemporaryDirectory


class TestAgentCoder(unittest.TestCase):
    """Test suite for the AgentCoder functionality."""

    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")
        self.original_cwd = os.getcwd()
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_agent_coder_creation(self):
        """Test that AgentCoder can be created with the 'agent' edit format."""
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io, edit_format="agent")

        # Check that the coder is an AgentCoder instance
        from aider.coders.agent_coder import AgentCoder
        self.assertIsInstance(coder, AgentCoder)
        self.assertEqual(coder.edit_format, "agent")

    def test_agent_coder_max_iterations(self):
        """Test that AgentCoder respects max iteration configuration."""
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(
            self.GPT35, None, io, edit_format="agent", max_agent_iterations=5
        )

        from aider.coders.agent_coder import AgentCoder
        self.assertIsInstance(coder, AgentCoder)
        self.assertEqual(coder.max_agent_iterations, 5)

    def test_agent_coder_auto_test_enabled(self):
        """Test that AgentCoder forces auto_test to be enabled."""
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(
            self.GPT35, None, io, edit_format="agent"
        )

        from aider.coders.agent_coder import AgentCoder
        self.assertIsInstance(coder, AgentCoder)
        # Agent mode forces auto_test to True
        self.assertTrue(coder.auto_test)

    def test_agent_command_exists(self):
        """Test that the /agent command exists and is registered."""
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Check that /agent is in the list of commands
        all_commands = commands.get_commands()
        self.assertIn("/agent", all_commands)

    def test_agent_command_switches_mode(self):
        """Test that /agent command switches to agent mode."""
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Test that calling /agent without args switches mode
        with self.assertRaises(SwitchCoder) as context:
            commands.cmd_agent("")

        # Check that it's switching to agent mode
        self.assertEqual(context.exception.kwargs.get("edit_format"), "agent")

    def test_agent_coder_iteration_tracking(self):
        """Test that AgentCoder tracks iterations correctly."""
        with GitTemporaryDirectory():
            io = InputOutput(pretty=False, fancy_input=False, yes=True)
            coder = Coder.create(
                self.GPT35,
                None,
                io,
                edit_format="agent",
                max_agent_iterations=2
            )

            from aider.coders.agent_coder import AgentCoder
            self.assertIsInstance(coder, AgentCoder)

            # Check initial state
            self.assertEqual(coder.agent_iteration_count, 0)
            self.assertEqual(coder.max_agent_iterations, 2)


class TestAgentCommand(unittest.TestCase):
    """Test suite for the /agent command."""

    def setUp(self):
        self.GPT35 = Model("gpt-3.5-turbo")
        self.original_cwd = os.getcwd()
        self.tempdir = tempfile.mkdtemp()
        os.chdir(self.tempdir)

    def tearDown(self):
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_agent_command_with_prompt(self):
        """Test /agent command with a prompt."""
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Mock the coder.run method to avoid actual LLM calls
        with patch.object(Coder, "run"):
            with self.assertRaises(SwitchCoder):
                commands.cmd_agent("Add a hello world function")

    def test_agent_in_chat_mode_list(self):
        """Test that agent mode appears in /chat-mode list."""
        io = InputOutput(pretty=False, fancy_input=False, yes=True)
        coder = Coder.create(self.GPT35, None, io)
        commands = Commands(io, coder)

        # Mock io.tool_output to capture output
        output_lines = []

        def mock_tool_output(line):
            output_lines.append(line)

        io.tool_output = mock_tool_output

        # Call chat_mode with no args to see the list
        commands.cmd_chat_mode("")

        # Check that agent mode is in the output
        all_output = "\n".join(output_lines)
        self.assertIn("agent", all_output)
        self.assertIn("Autonomous agent mode", all_output)


if __name__ == "__main__":
    unittest.main()
