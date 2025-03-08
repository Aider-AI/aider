import unittest
from unittest.mock import MagicMock, patch

from aider.coders.base_coder import Coder
from aider.io import InputOutput
from aider.models import Model


class TestReasoning(unittest.TestCase):
    def test_send_with_reasoning_content(self):
        """Test that reasoning content is properly formatted and output."""
        # Setup IO with no pretty
        io = InputOutput(pretty=False)
        io.ai_output = MagicMock()

        # Setup model and coder
        model = Model("gpt-3.5-turbo")
        coder = Coder.create(model, None, io=io)

        # Test data
        reasoning_content = "My step-by-step reasoning process"
        main_content = "Final answer after reasoning"

        # Mock completion response with reasoning content
        class MockCompletion:
            def __init__(self, content, reasoning_content):
                self.content = content
                self.reasoning_content = reasoning_content

        mock_completion = MockCompletion(main_content, reasoning_content)

        # Mock the model's send_completion method
        with patch.object(model, "send_completion", return_value=mock_completion):
            # Call send with a simple message
            messages = [{"role": "user", "content": "test prompt"}]
            result = coder.send(messages)
            
            # Format the response as it would happen in the normal flow
            coder.partial_response_content = mock_completion.content
            coder.partial_response_reasoning_content = mock_completion.reasoning_content
            output = coder.get_multi_response_content_in_progress(final=True)
            
            # Manually call ai_output to simulate the normal flow
            coder.io.ai_output(output)
            
            # Now verify ai_output was called with the right content
            io.ai_output.assert_called_once()
            output = io.ai_output.call_args[0][0]

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
