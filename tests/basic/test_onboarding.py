import argparse
import base64
import hashlib
import os
import unittest
from unittest.mock import MagicMock, patch

import requests

# Import the functions to be tested
from aider.onboarding import (
    check_openrouter_tier,
    exchange_code_for_key,
    find_available_port,
    generate_pkce_codes,
    offer_openrouter_oauth,
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
        self.assertEqual(
            try_to_select_default_model(), "openrouter/google/gemini-2.5-pro-exp-03-25:free"
        )
        mock_check_tier.assert_called_once_with("or_key")

    @patch("aider.onboarding.check_openrouter_tier", return_value=False)  # Assume paid tier
    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "or_key"}, clear=True)
    def test_try_select_default_model_openrouter_paid(self, mock_check_tier):
        """Test OpenRouter paid model selection."""
        self.assertEqual(try_to_select_default_model(), "openrouter/anthropic/claude-3.7-sonnet")
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
        self.assertEqual(try_to_select_default_model(), "openrouter/anthropic/claude-3.7-sonnet")
        mock_check_tier.assert_called_once_with("or_key")

    @patch("aider.onboarding.check_openrouter_tier")
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "an_key", "OPENAI_API_KEY": "oa_key"}, clear=True)
    def test_try_select_default_model_priority_anthropic(self, mock_check_tier):
        """Test Anthropic key takes priority over OpenAI."""
        self.assertEqual(try_to_select_default_model(), "sonnet")
        mock_check_tier.assert_not_called()

    @patch("socketserver.TCPServer")
    def test_find_available_port_success(self, mock_tcp_server):
        """Test finding an available port."""
        # Simulate port 8484 being available
        mock_tcp_server.return_value.__enter__.return_value = None  # Allow context manager
        port = find_available_port(start_port=8484, end_port=8484)
        self.assertEqual(port, 8484)
        mock_tcp_server.assert_called_once_with(("localhost", 8484), None)

    @patch("socketserver.TCPServer")
    def test_find_available_port_in_use(self, mock_tcp_server):
        """Test finding the next available port if the first is in use."""
        # Simulate port 8484 raising OSError, 8485 being available
        mock_tcp_server.side_effect = [OSError, MagicMock()]
        mock_tcp_server.return_value.__enter__.return_value = None  # Allow context manager
        port = find_available_port(start_port=8484, end_port=8485)
        self.assertEqual(port, 8485)
        self.assertEqual(mock_tcp_server.call_count, 2)
        mock_tcp_server.assert_any_call(("localhost", 8484), None)
        mock_tcp_server.assert_any_call(("localhost", 8485), None)

    @patch("socketserver.TCPServer", side_effect=OSError)
    def test_find_available_port_none_available(self, mock_tcp_server):
        """Test returning None if no ports are available in the range."""
        port = find_available_port(start_port=8484, end_port=8485)
        self.assertIsNone(port)
        self.assertEqual(mock_tcp_server.call_count, 2)  # Tried 8484 and 8485

    def test_generate_pkce_codes(self):
        """Test PKCE code generation."""
        verifier, challenge = generate_pkce_codes()
        self.assertIsInstance(verifier, str)
        self.assertIsInstance(challenge, str)
        self.assertGreater(len(verifier), 40)  # Check reasonable length
        self.assertGreater(len(challenge), 40)
        # Verify the challenge is the SHA256 hash of the verifier, base64 encoded
        hasher = hashlib.sha256()
        hasher.update(verifier.encode("utf-8"))
        expected_challenge = base64.urlsafe_b64encode(hasher.digest()).rstrip(b"=").decode("utf-8")
        self.assertEqual(challenge, expected_challenge)

    @patch("requests.post")
    def test_exchange_code_for_key_success(self, mock_post):
        """Test successful code exchange for API key."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "test_api_key"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        io_mock = DummyIO()

        api_key = exchange_code_for_key("auth_code", "verifier", io_mock)

        self.assertEqual(api_key, "test_api_key")
        mock_post.assert_called_once_with(
            "https://openrouter.ai/api/v1/auth/keys",
            headers={"Content-Type": "application/json"},
            json={
                "code": "auth_code",
                "code_verifier": "verifier",
                "code_challenge_method": "S256",
            },
            timeout=30,
        )

    @patch("requests.post")
    def test_exchange_code_for_key_missing_key(self, mock_post):
        """Test code exchange when 'key' is missing in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"other_data": "value"}  # Missing 'key'
        mock_response.raise_for_status.return_value = None
        mock_response.text = '{"other_data": "value"}'
        mock_post.return_value = mock_response
        io_mock = DummyIO()
        io_mock.tool_error = MagicMock()  # Track error output

        api_key = exchange_code_for_key("auth_code", "verifier", io_mock)

        self.assertIsNone(api_key)
        io_mock.tool_error.assert_any_call("Error: 'key' not found in OpenRouter response.")
        io_mock.tool_error.assert_any_call('Response: {"other_data": "value"}')

    @patch("requests.post")
    def test_exchange_code_for_key_http_error(self, mock_post):
        """Test code exchange with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.reason = "Bad Request"
        mock_response.text = '{"error": "invalid_code"}'
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_post.side_effect = http_error
        io_mock = DummyIO()
        io_mock.tool_error = MagicMock()

        api_key = exchange_code_for_key("auth_code", "verifier", io_mock)

        self.assertIsNone(api_key)
        io_mock.tool_error.assert_any_call(
            "Error exchanging code for OpenRouter key: 400 Bad Request"
        )
        io_mock.tool_error.assert_any_call('Response: {"error": "invalid_code"}')

    @patch("requests.post")
    def test_exchange_code_for_key_timeout(self, mock_post):
        """Test code exchange with timeout."""
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")
        io_mock = DummyIO()
        io_mock.tool_error = MagicMock()

        api_key = exchange_code_for_key("auth_code", "verifier", io_mock)

        self.assertIsNone(api_key)
        io_mock.tool_error.assert_called_once_with(
            "Error: Request to OpenRouter timed out during code exchange."
        )

    @patch("requests.post")
    def test_exchange_code_for_key_request_exception(self, mock_post):
        """Test code exchange with general request exception."""
        req_exception = requests.exceptions.RequestException("Network Error")
        mock_post.side_effect = req_exception
        io_mock = DummyIO()
        io_mock.tool_error = MagicMock()

        api_key = exchange_code_for_key("auth_code", "verifier", io_mock)

        self.assertIsNone(api_key)
        io_mock.tool_error.assert_called_once_with(
            f"Error exchanging code for OpenRouter key: {req_exception}"
        )

    # --- Tests for select_default_model ---

    @patch("aider.onboarding.try_to_select_default_model", return_value="gpt-4o")
    @patch("aider.onboarding.offer_openrouter_oauth")
    def test_select_default_model_already_specified(self, mock_offer_oauth, mock_try_select):
        """Test select_default_model returns args.model if provided."""
        args = argparse.Namespace(model="specific-model")
        io_mock = DummyIO()
        analytics_mock = DummyAnalytics()
        selected_model = select_default_model(args, io_mock, analytics_mock)
        self.assertEqual(selected_model, "specific-model")
        mock_try_select.assert_not_called()
        mock_offer_oauth.assert_not_called()

    @patch("aider.onboarding.try_to_select_default_model", return_value="gpt-4o")
    @patch("aider.onboarding.offer_openrouter_oauth")
    def test_select_default_model_found_via_env(self, mock_offer_oauth, mock_try_select):
        """Test select_default_model returns model found by try_to_select."""
        args = argparse.Namespace(model=None)  # No model specified
        io_mock = DummyIO()
        io_mock.tool_warning = MagicMock()  # Track warnings
        analytics_mock = DummyAnalytics()
        analytics_mock.event = MagicMock()  # Track events

        selected_model = select_default_model(args, io_mock, analytics_mock)

        self.assertEqual(selected_model, "gpt-4o")
        mock_try_select.assert_called_once()
        io_mock.tool_warning.assert_called_once_with(
            "Using gpt-4o model with API key from environment."
        )
        analytics_mock.event.assert_called_once_with("auto_model_selection", model="gpt-4o")
        mock_offer_oauth.assert_not_called()

    @patch(
        "aider.onboarding.try_to_select_default_model", side_effect=[None, None]
    )  # Fails first, fails after oauth attempt
    @patch(
        "aider.onboarding.offer_openrouter_oauth", return_value=False
    )  # OAuth offered but fails/declined
    def test_select_default_model_no_keys_oauth_fail(self, mock_offer_oauth, mock_try_select):
        """Test select_default_model offers OAuth when no keys, but OAuth fails."""
        args = argparse.Namespace(model=None)
        io_mock = DummyIO()
        io_mock.tool_warning = MagicMock()
        io_mock.offer_url = MagicMock()
        analytics_mock = DummyAnalytics()

        selected_model = select_default_model(args, io_mock, analytics_mock)

        self.assertIsNone(selected_model)
        self.assertEqual(mock_try_select.call_count, 2)  # Called before and after oauth attempt
        mock_offer_oauth.assert_called_once_with(io_mock, analytics_mock)
        io_mock.tool_warning.assert_called_once_with(
            "No LLM model was specified and no API keys were provided."
        )
        io_mock.offer_url.assert_called_once()  # Should offer docs URL

    @patch(
        "aider.onboarding.try_to_select_default_model",
        side_effect=[None, "openrouter/google/gemini-2.5-pro-exp-03-25:free"],
    )  # Fails first, succeeds after oauth
    @patch(
        "aider.onboarding.offer_openrouter_oauth", return_value=True
    )  # OAuth offered and succeeds
    def test_select_default_model_no_keys_oauth_success(self, mock_offer_oauth, mock_try_select):
        """Test select_default_model offers OAuth, which succeeds."""
        args = argparse.Namespace(model=None)
        io_mock = DummyIO()
        io_mock.tool_warning = MagicMock()
        analytics_mock = DummyAnalytics()

        selected_model = select_default_model(args, io_mock, analytics_mock)

        self.assertEqual(selected_model, "openrouter/google/gemini-2.5-pro-exp-03-25:free")
        self.assertEqual(mock_try_select.call_count, 2)  # Called before and after oauth
        mock_offer_oauth.assert_called_once_with(io_mock, analytics_mock)
        # Only one warning is expected: "No LLM model..."
        self.assertEqual(io_mock.tool_warning.call_count, 1)
        io_mock.tool_warning.assert_called_once_with(
            "No LLM model was specified and no API keys were provided."
        )
        # The second call to try_select finds the model, so the *outer* function logs the usage.
        # Note: The warning comes from the second call within select_default_model,
        # not try_select itself.
        # We verify the final state and model returned.

    # --- Tests for offer_openrouter_oauth ---
    @patch("aider.onboarding.start_openrouter_oauth_flow", return_value="new_or_key")
    @patch.dict(os.environ, {}, clear=True)  # Ensure no key exists initially
    def test_offer_openrouter_oauth_confirm_yes_success(self, mock_start_oauth):
        """Test offer_openrouter_oauth when user confirms and OAuth succeeds."""
        io_mock = DummyIO()
        io_mock.confirm_ask = MagicMock(return_value=True)  # User says yes
        analytics_mock = DummyAnalytics()
        analytics_mock.event = MagicMock()

        result = offer_openrouter_oauth(io_mock, analytics_mock)

        self.assertTrue(result)
        io_mock.confirm_ask.assert_called_once()
        mock_start_oauth.assert_called_once_with(io_mock, analytics_mock)
        self.assertEqual(os.environ.get("OPENROUTER_API_KEY"), "new_or_key")
        analytics_mock.event.assert_any_call("oauth_flow_initiated", provider="openrouter")
        analytics_mock.event.assert_any_call("oauth_flow_success")
        # Clean up env var
        del os.environ["OPENROUTER_API_KEY"]

    @patch("aider.onboarding.start_openrouter_oauth_flow", return_value=None)  # OAuth fails
    @patch.dict(os.environ, {}, clear=True)
    def test_offer_openrouter_oauth_confirm_yes_fail(self, mock_start_oauth):
        """Test offer_openrouter_oauth when user confirms but OAuth fails."""
        io_mock = DummyIO()
        io_mock.confirm_ask = MagicMock(return_value=True)  # User says yes
        io_mock.tool_error = MagicMock()
        analytics_mock = DummyAnalytics()
        analytics_mock.event = MagicMock()

        result = offer_openrouter_oauth(io_mock, analytics_mock)

        self.assertFalse(result)
        io_mock.confirm_ask.assert_called_once()
        mock_start_oauth.assert_called_once_with(io_mock, analytics_mock)
        self.assertNotIn("OPENROUTER_API_KEY", os.environ)
        io_mock.tool_error.assert_called_once_with(
            "OpenRouter authentication did not complete successfully."
        )
        analytics_mock.event.assert_any_call("oauth_flow_initiated", provider="openrouter")
        analytics_mock.event.assert_any_call("oauth_flow_failure")

    @patch("aider.onboarding.start_openrouter_oauth_flow")
    def test_offer_openrouter_oauth_confirm_no(self, mock_start_oauth):
        """Test offer_openrouter_oauth when user declines."""
        io_mock = DummyIO()
        io_mock.confirm_ask = MagicMock(return_value=False)  # User says no
        analytics_mock = DummyAnalytics()
        analytics_mock.event = MagicMock()

        result = offer_openrouter_oauth(io_mock, analytics_mock)

        self.assertFalse(result)
        io_mock.confirm_ask.assert_called_once()
        mock_start_oauth.assert_not_called()
        analytics_mock.event.assert_not_called()  # No OAuth events if declined

    # --- More complex test for start_openrouter_oauth_flow (simplified) ---
    # This test focuses on the successful path, mocking heavily


if __name__ == "__main__":
    unittest.main()
