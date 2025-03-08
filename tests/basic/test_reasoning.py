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

    def test_send_with_reasoning_content_stream(self):
        """Test that streaming reasoning content is properly formatted and output."""
        # Setup IO with pretty output for streaming
        io = InputOutput(pretty=True)
        mock_mdstream = MagicMock()
        io.get_assistant_mdstream = MagicMock(return_value=mock_mdstream)

        # Setup model and coder
        model = Model("gpt-3.5-turbo")
        coder = Coder.create(model, None, io=io, stream=True)

        # Ensure the coder shows pretty output
        coder.show_pretty = MagicMock(return_value=True)

        # Mock streaming response chunks
        class MockStreamingChunk:
            def __init__(self, content=None, reasoning_content=None, finish_reason=None):
                self.choices = [MagicMock()]
                self.choices[0].delta = MagicMock()
                self.choices[0].finish_reason = finish_reason

                # Set content if provided
                if content is not None:
                    self.choices[0].delta.content = content
                else:
                    # Need to handle attribute access that would raise AttributeError
                    delattr(self.choices[0].delta, "content")

                # Set reasoning_content if provided
                if reasoning_content is not None:
                    self.choices[0].delta.reasoning_content = reasoning_content
                else:
                    # Need to handle attribute access that would raise AttributeError
                    delattr(self.choices[0].delta, "reasoning_content")

        # Create chunks to simulate streaming
        chunks = [
            # First chunk with reasoning content starts the tag
            MockStreamingChunk(reasoning_content="My step-by-step "),
            # Additional reasoning content
            MockStreamingChunk(reasoning_content="reasoning process"),
            # Switch to main content - this will automatically end the reasoning tag
            MockStreamingChunk(content="Final "),
            # More main content
            MockStreamingChunk(content="answer "),
            MockStreamingChunk(content="after reasoning"),
            # End the response
            MockStreamingChunk(finish_reason="stop"),
        ]

        # Create a mock hash object
        mock_hash = MagicMock()
        mock_hash.hexdigest.return_value = "mock_hash_digest"

        # Mock the model's send_completion to return the hash and completion
        with patch.object(model, "send_completion", return_value=(mock_hash, chunks)):
            # Set mdstream directly on the coder object
            coder.mdstream = mock_mdstream

            # Call send with a simple message
            messages = [{"role": "user", "content": "test prompt"}]
            list(coder.send(messages))

            # Verify mdstream.update was called multiple times
            mock_mdstream.update.assert_called()

            # Explicitly get all calls to update
            update_calls = mock_mdstream.update.call_args_list

            # There should be at least two calls - one for streaming and one final
            self.assertGreaterEqual(
                len(update_calls), 2, "Should have at least two calls to update (streaming + final)"
            )

            # Check that at least one call has final=True (should be the last one)
            has_final_true = any(call[1].get("final", False) for call in update_calls)
            self.assertTrue(has_final_true, "At least one update call should have final=True")

            # Get the text from the last update call
            final_text = update_calls[-1][0][0]

            # The final text should include both reasoning and main content with proper formatting
            self.assertIn("> Thinking ...", final_text)
            self.assertIn("My step-by-step reasoning process", final_text)
            self.assertIn("> ... done thinking", final_text)
            self.assertIn("Final answer after reasoning", final_text)

            # Ensure proper order: reasoning first, then main content
            reasoning_pos = final_text.find("My step-by-step reasoning process")
            main_pos = final_text.find("Final answer after reasoning")
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
