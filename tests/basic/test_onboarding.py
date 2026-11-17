import argparse
import os
import unittest
from unittest.mock import MagicMock, patch

import requests

# Import the functions to be tested
from aider.onboarding import (
    check_openrouter_tier,
    select_default_model,
    try_to_select_default_model,
)


# Mock the Analytics class as it's used in some functions
class DummyAnalytics:
    def event(self, *args, **kwargs):
        pass


# Mock the InputOutput class
class DummyIO:
    def tool_output(self, *args, **kwargs):
        pass

    def tool_warning(self, *args, **kwargs):
        pass

    def tool_error(self, *args, **kwargs):
        pass

    def confirm_ask(self, *args, **kwargs):
        return False  # Default to no confirmation

    def offer_url(self, *args, **kwargs):
        pass


class TestOnboarding(unittest.TestCase):
    @patch("requests.get")
    def test_check_openrouter_tier_free(self, mock_get):
        """Test check_openrouter_tier identifies free tier."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"is_free_tier": True}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        self.assertTrue(check_openrouter_tier("fake_key"))
        mock_get.assert_called_once_with(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": "Bearer fake_key"},
            timeout=5,
        )

    @patch("requests.get")
    def test_check_openrouter_tier_paid(self, mock_get):
        """Test check_openrouter_tier identifies paid tier."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"is_free_tier": False}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        self.assertFalse(check_openrouter_tier("fake_key"))

    @patch("requests.get")
    def test_check_openrouter_tier_api_error(self, mock_get):
        """Test check_openrouter_tier defaults to free on API error."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        self.assertTrue(check_openrouter_tier("fake_key"))

    @patch("requests.get")
    def test_check_openrouter_tier_missing_key(self, mock_get):
        """Test check_openrouter_tier defaults to free if key is missing in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {}}  # Missing 'is_free_tier'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        self.assertTrue(check_openrouter_tier("fake_key"))

    @patch("aider.onboarding.check_openrouter_tier")
    @patch.dict(os.environ, {}, clear=True)
    def test_try_select_default_model_no_keys(self, mock_check_tier):
        """Test no model is selected when no keys are present."""
        self.assertIsNone(try_to_select_default_model())
        mock_check_tier.assert_not_called()

    @patch("aider.onboarding.check_openrouter_tier", return_value=True)  # Assume free tier
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "or_key"}, clear=True)
    def test_try_select_default_model_openrouter_free(self, mock_check_tier):
        """Test OpenRouter free model selection."""
        self.assertEqual(try_to_select_default_model(), "openrouter/deepseek/deepseek-r1:free")
        mock_check_tier.assert_called_once_with("or_key")

    @patch("aider.onboarding.check_openrouter_tier", return_value=False)  # Assume paid tier
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "or_key"}, clear=True)
    def test_try_select_default_model_openrouter_paid(self, mock_check_tier):
        """Test OpenRouter paid model selection."""
        self.assertEqual(try_to_select_default_model(), "openrouter/anthropic/claude-sonnet-4")
        mock_check_tier.assert_called_once_with("or_key")

    @patch("aider.onboarding.check_openrouter_tier")
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "an_key"}, clear=True)
    def test_try_select_default_model_anthropic(self, mock_check_tier):
        """Test Anthropic model selection."""
        self.assertEqual(try_to_select_default_model(), "sonnet")
        mock_check_tier.assert_not_called()

    @patch("aider.onboarding.check_openrouter_tier")
    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "ds_key"}, clear=True)
    def test_try_select_default_model_deepseek(self, mock_check_tier):
        """Test Deepseek model selection."""
        self.assertEqual(try_to_select_default_model(), "deepseek")
        mock_check_tier.assert_not_called()

    @patch("aider.onboarding.check_openrouter_tier")
    @patch.dict(os.environ, {"OPENAI_API_KEY": "oa_key"}, clear=True)
    def test_try_select_default_model_openai(self, mock_check_tier):
        """Test OpenAI model selection."""
        self.assertEqual(try_to_select_default_model(), "gpt-4o")
        mock_check_tier.assert_not_called()

    @patch("aider.onboarding.check_openrouter_tier")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "gm_key"}, clear=True)
    def test_try_select_default_model_gemini(self, mock_check_tier):
        """Test Gemini model selection."""
        self.assertEqual(try_to_select_default_model(), "gemini/gemini-2.5-pro-exp-03-25")
        mock_check_tier.assert_not_called()

    @patch("aider.onboarding.check_openrouter_tier")
    @patch.dict(os.environ, {"VERTEXAI_PROJECT": "vx_proj"}, clear=True)
    def test_try_select_default_model_vertex(self, mock_check_tier):
        """Test Vertex AI model selection."""
        self.assertEqual(try_to_select_default_model(), "vertex_ai/gemini-2.5-pro-exp-03-25")
        mock_check_tier.assert_not_called()

    @patch("aider.onboarding.check_openrouter_tier", return_value=False)  # Paid
    @patch.dict(
        os.environ, {"OPENROUTER_API_KEY": "or_key", "OPENAI_API_KEY": "oa_key"}, clear=True
    )
    def test_try_select_default_model_priority_openrouter(self, mock_check_tier):
        """Test OpenRouter key takes priority."""
        self.assertEqual(try_to_select_default_model(), "openrouter/anthropic/claude-sonnet-4")
        mock_check_tier.assert_called_once_with("or_key")

    @patch("aider.onboarding.check_openrouter_tier")
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "an_key", "OPENAI_API_KEY": "oa_key"}, clear=True)
    def test_try_select_default_model_priority_anthropic(self, mock_check_tier):
        """Test Anthropic key takes priority over OpenAI."""
        self.assertEqual(try_to_select_default_model(), "sonnet")
        mock_check_tier.assert_not_called()

    # --- Tests for select_default_model (sign-in now lives in `aider --login`) ---

    @patch("aider.onboarding.try_to_select_default_model", return_value="gpt-4o")
    def test_select_default_model_already_specified(self, mock_try_select):
        """select_default_model returns args.model if provided."""
        args = argparse.Namespace(model="specific-model")
        selected_model = select_default_model(args, DummyIO(), DummyAnalytics())
        self.assertEqual(selected_model, "specific-model")
        mock_try_select.assert_not_called()

    @patch("aider.onboarding.try_to_select_default_model", return_value="gpt-4o")
    def test_select_default_model_found_via_env(self, mock_try_select):
        args = argparse.Namespace(model=None)
        self.assertEqual(select_default_model(args, DummyIO(), DummyAnalytics()), "gpt-4o")

    @patch("aider.onboarding.try_to_select_default_model", return_value=None)
    def test_select_default_model_no_keys_returns_none_without_oauth(self, mock_try_select):
        """With no keys there is no automatic login; the user is pointed to --login."""
        args = argparse.Namespace(model=None)
        io = MagicMock()
        self.assertIsNone(select_default_model(args, io, DummyAnalytics()))
        warnings = [str(call.args[0]) for call in io.tool_warning.call_args_list]
        self.assertTrue(any("--login openrouter" in message for message in warnings))


if __name__ == "__main__":
    unittest.main()
