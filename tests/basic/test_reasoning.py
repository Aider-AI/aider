import unittest
from unittest.mock import MagicMock, patch

from aider.coders.base_coder import Coder
from aider.dump import dump  # noqa
from aider.io import InputOutput
from aider.models import Model


class TestReasoning(unittest.TestCase):
    def test_send_with_reasoning_content(self):
        """Test that reasoning content is properly formatted and output."""
        # Setup IO with no pretty
        io = InputOutput(pretty=False)
        io.assistant_output = MagicMock()

        # Setup model and coder
        model = Model("gpt-3.5-turbo")
        coder = Coder.create(model, None, io=io, stream=False)

        # Test data
        reasoning_content = "My step-by-step reasoning process"
        main_content = "Final answer after reasoning"

        # Mock completion response with reasoning content
        class MockCompletion:
            def __init__(self, content, reasoning_content):
                self.content = content
                # Add required attributes expected by show_send_output
                self.choices = [MagicMock()]
                self.choices[0].message.content = content
                self.choices[0].message.reasoning_content = reasoning_content
                self.finish_reason = "stop"

        mock_completion = MockCompletion(main_content, reasoning_content)

        # Create a mock hash object
        mock_hash = MagicMock()
        mock_hash.hexdigest.return_value = "mock_hash_digest"

        # Mock the model's send_completion method to return the expected tuple format
        with patch.object(model, "send_completion", return_value=(mock_hash, mock_completion)):
            # Call send with a simple message
            messages = [{"role": "user", "content": "test prompt"}]
            list(coder.send(messages))

            # Now verify ai_output was called with the right content
            io.assistant_output.assert_called_once()
            output = io.assistant_output.call_args[0][0]

            dump(output)

            # Output should contain formatted reasoning tags
            self.assertIn("Thinking ...", output)
            self.assertIn("... done thinking", output)

            # Output should include both reasoning and main content
            self.assertIn(reasoning_content, output)
            self.assertIn(main_content, output)

            # Ensure proper order: reasoning first, then main content
            reasoning_pos = output.find(reasoning_content)
            main_pos = output.find(main_content)
            self.assertLess(
                reasoning_pos, main_pos, "Reasoning content should appear before main content"
            )

    def test_send_with_think_tags(self):
        """Test that <think> tags are properly processed and formatted."""
        # Setup IO with no pretty
        io = InputOutput(pretty=False)
        io.assistant_output = MagicMock()

        # Setup model and coder
        model = Model("gpt-3.5-turbo")
        model.remove_reasoning = "think"  # Set to remove <think> tags
        coder = Coder.create(model, None, io=io, stream=False)

        # Test data
        reasoning_content = "My step-by-step reasoning process"
        main_content = "Final answer after reasoning"

        # Create content with think tags
        combined_content = f"""<think>
{reasoning_content}
</think>

{main_content}"""

        # Mock completion response with think tags in content
        class MockCompletion:
            def __init__(self, content):
                self.content = content
                # Add required attributes expected by show_send_output
                self.choices = [MagicMock()]
                self.choices[0].message.content = content
                self.choices[0].message.reasoning_content = None  # No separate reasoning_content
                self.finish_reason = "stop"

        mock_completion = MockCompletion(combined_content)

        # Create a mock hash object
        mock_hash = MagicMock()
        mock_hash.hexdigest.return_value = "mock_hash_digest"

        # Mock the model's send_completion method to return the expected tuple format
        with patch.object(model, "send_completion", return_value=(mock_hash, mock_completion)):
            # Call send with a simple message
            messages = [{"role": "user", "content": "test prompt"}]
            list(coder.send(messages))

            # Now verify ai_output was called with the right content
            io.assistant_output.assert_called_once()
            output = io.assistant_output.call_args[0][0]

            dump(output)

            # Output should contain formatted reasoning tags
            self.assertIn("Thinking ...", output)
            self.assertIn("... done thinking", output)

            # Output should include both reasoning and main content
            self.assertIn(reasoning_content, output)
            self.assertIn(main_content, output)

            # Ensure proper order: reasoning first, then main content
            reasoning_pos = output.find(reasoning_content)
            main_pos = output.find(main_content)
            self.assertLess(
                reasoning_pos, main_pos, "Reasoning content should appear before main content"
            )


if __name__ == "__main__":
    unittest.main()
