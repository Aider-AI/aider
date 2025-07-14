from unittest.mock import MagicMock, patch

from aider.coders.base_coder import Coder
from aider.io import InputOutput
from aider.models import Model


class TestAskCoder:
    def test_ask_coder_uses_ask_model(self, monkeypatch):
        # Set environment variables for API keys
        monkeypatch.setenv("OPENAI_API_KEY", "test_key")

        # Create a main model and an ask model
        main_model = Model("gpt-4")
        ask_model = Model("gpt-3.5-turbo")
        main_model.ask_model = ask_model

        io = InputOutput(pretty=False, yes=True)

        # Create an AskCoder instance
        coder = Coder.create(main_model=main_model, edit_format="ask", io=io)

        # Mock litellm.completion to capture the model name
        with patch("litellm.completion") as mock_completion:
            mock_completion.return_value = [MagicMock()]  # stream
            # Run a message in ask mode
            list(coder.run_stream("What is the meaning of life?"))

            # Assert that the completion was called with the ask model
            mock_completion.assert_called_once()
            assert mock_completion.call_args.kwargs["model"] == ask_model.name
