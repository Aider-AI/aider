import unittest
from unittest.mock import ANY, MagicMock, patch

from aider.models import (
    ANTHROPIC_BETA_HEADER,
    Model,
    ModelInfoManager,
    register_models,
    sanity_check_model,
    sanity_check_models,
)


class TestModels(unittest.TestCase):
    def setUp(self):
        """Reset MODEL_SETTINGS before each test"""
        from aider.models import MODEL_SETTINGS

        self._original_settings = MODEL_SETTINGS.copy()

    def tearDown(self):
        """Restore original MODEL_SETTINGS after each test"""
        from aider.models import MODEL_SETTINGS

        MODEL_SETTINGS.clear()
        MODEL_SETTINGS.extend(self._original_settings)

    def test_get_model_info_nonexistent(self):
        manager = ModelInfoManager()
        info = manager.get_model_info("non-existent-model")
        self.assertEqual(info, {})

    def test_max_context_tokens(self):
        model = Model("gpt-3.5-turbo")
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = Model("gpt-3.5-turbo-16k")
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = Model("gpt-3.5-turbo-1106")
        self.assertEqual(model.info["max_input_tokens"], 16385)

        model = Model("gpt-4")
        self.assertEqual(model.info["max_input_tokens"], 8 * 1024)

        model = Model("gpt-4-32k")
        self.assertEqual(model.info["max_input_tokens"], 32 * 1024)

        model = Model("gpt-4-0613")
        self.assertEqual(model.info["max_input_tokens"], 8 * 1024)

    @patch("os.environ")
    def test_sanity_check_model_all_set(self, mock_environ):
        mock_environ.get.return_value = "dummy_value"
        mock_io = MagicMock()
        model = MagicMock()
        model.name = "test-model"
        model.missing_keys = ["API_KEY1", "API_KEY2"]
        model.keys_in_environment = True
        model.info = {"some": "info"}

        sanity_check_model(mock_io, model)

        mock_io.tool_output.assert_called()
        calls = mock_io.tool_output.call_args_list
        self.assertIn("- API_KEY1: Set", str(calls))
        self.assertIn("- API_KEY2: Set", str(calls))

    @patch("os.environ")
    def test_sanity_check_model_not_set(self, mock_environ):
        mock_environ.get.return_value = ""
        mock_io = MagicMock()
        model = MagicMock()
        model.name = "test-model"
        model.missing_keys = ["API_KEY1", "API_KEY2"]
        model.keys_in_environment = True
        model.info = {"some": "info"}

        sanity_check_model(mock_io, model)

        mock_io.tool_output.assert_called()
        calls = mock_io.tool_output.call_args_list
        self.assertIn("- API_KEY1: Not set", str(calls))
        self.assertIn("- API_KEY2: Not set", str(calls))

    def test_sanity_check_models_bogus_editor(self):
        mock_io = MagicMock()
        main_model = Model("gpt-4")
        main_model.editor_model = Model("bogus-model")

        result = sanity_check_models(mock_io, main_model)

        self.assertTrue(
            result
        )  # Should return True because there's a problem with the editor model
        mock_io.tool_warning.assert_called_with(ANY)  # Ensure a warning was issued

        warning_messages = [
            warning_call.args[0] for warning_call in mock_io.tool_warning.call_args_list
        ]
        print("Warning messages:", warning_messages)  # Add this line

        self.assertGreaterEqual(mock_io.tool_warning.call_count, 1)  # Expect two warnings
        self.assertTrue(
            any("bogus-model" in msg for msg in warning_messages)
        )  # Check that one of the warnings mentions the bogus model

    def test_model_aliases(self):
        # Test common aliases
        model = Model("4")
        self.assertEqual(model.name, "gpt-4-0613")

        model = Model("4o")
        self.assertEqual(model.name, "gpt-4o")

        model = Model("35turbo")
        self.assertEqual(model.name, "gpt-3.5-turbo")

        model = Model("35-turbo")
        self.assertEqual(model.name, "gpt-3.5-turbo")

        model = Model("3")
        self.assertEqual(model.name, "gpt-3.5-turbo")

        model = Model("sonnet")
        self.assertEqual(model.name, "claude-3-5-sonnet-20241022")

        model = Model("haiku")
        self.assertEqual(model.name, "claude-3-5-haiku-20241022")

        model = Model("opus")
        self.assertEqual(model.name, "claude-3-opus-20240229")

        # Test non-alias passes through unchanged
        model = Model("gpt-4")
        self.assertEqual(model.name, "gpt-4")

    def test_o1_use_temp_false(self):
        # Test GitHub Copilot models
        model = Model("github/o1-mini")
        self.assertEqual(model.name, "github/o1-mini")
        self.assertEqual(model.use_temperature, False)

        model = Model("github/o1-preview")
        self.assertEqual(model.name, "github/o1-preview")
        self.assertEqual(model.use_temperature, False)

    def test_get_repo_map_tokens(self):
        # Test default case (no max_input_tokens in info)
        model = Model("gpt-4")
        model.info = {}
        self.assertEqual(model.get_repo_map_tokens(), 1024)

        # Test minimum boundary (max_input_tokens < 8192)
        model.info = {"max_input_tokens": 4096}
        self.assertEqual(model.get_repo_map_tokens(), 1024)

        # Test middle range (max_input_tokens = 16384)
        model.info = {"max_input_tokens": 16384}
        self.assertEqual(model.get_repo_map_tokens(), 2048)

        # Test maximum boundary (max_input_tokens > 32768)
        model.info = {"max_input_tokens": 65536}
        self.assertEqual(model.get_repo_map_tokens(), 4096)

        # Test exact boundary values
        model.info = {"max_input_tokens": 8192}
        self.assertEqual(model.get_repo_map_tokens(), 1024)

        model.info = {"max_input_tokens": 32768}
        self.assertEqual(model.get_repo_map_tokens(), 4096)

    def test_configure_model_settings(self):
        # Test o3-mini case
        model = Model("something/o3-mini")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertFalse(model.use_temperature)

        # Test o1-mini case
        model = Model("something/o1-mini")
        self.assertTrue(model.use_repo_map)
        self.assertFalse(model.use_temperature)
        self.assertFalse(model.use_system_prompt)

        # Test o1-preview case
        model = Model("something/o1-preview")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertFalse(model.use_temperature)
        self.assertFalse(model.use_system_prompt)

        # Test o1 case
        model = Model("something/o1")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertFalse(model.use_temperature)
        self.assertFalse(model.streaming)

        # Test deepseek v3 case
        model = Model("deepseek-v3")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertEqual(model.reminder, "sys")
        self.assertTrue(model.examples_as_sys_msg)

        # Test deepseek reasoner case
        model = Model("deepseek-r1")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertTrue(model.examples_as_sys_msg)
        self.assertFalse(model.use_temperature)
        self.assertEqual(model.remove_reasoning, "think")

        # Test provider/deepseek-r1 case
        model = Model("someprovider/deepseek-r1")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertTrue(model.examples_as_sys_msg)
        self.assertFalse(model.use_temperature)
        self.assertEqual(model.remove_reasoning, "think")

        # Test provider/deepseek-v3 case
        model = Model("anotherprovider/deepseek-v3")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertEqual(model.reminder, "sys")
        self.assertTrue(model.examples_as_sys_msg)

        # Test llama3 70b case
        model = Model("llama3-70b")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertTrue(model.send_undo_reply)
        self.assertTrue(model.examples_as_sys_msg)

        # Test gpt-4 case
        model = Model("gpt-4")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertTrue(model.send_undo_reply)

        # Test gpt-3.5 case
        model = Model("gpt-3.5")
        self.assertEqual(model.reminder, "sys")

        # Test 3.5-sonnet case
        model = Model("claude-3.5-sonnet")
        self.assertEqual(model.edit_format, "diff")
        self.assertTrue(model.use_repo_map)
        self.assertTrue(model.examples_as_sys_msg)
        self.assertEqual(model.reminder, "user")

        # Test o1- prefix case
        model = Model("o1-something")
        self.assertFalse(model.use_system_prompt)
        self.assertFalse(model.use_temperature)

        # Test qwen case
        model = Model("qwen-coder-2.5-32b")
        self.assertEqual(model.edit_format, "diff")
        self.assertEqual(model.editor_edit_format, "editor-diff")
        self.assertTrue(model.use_repo_map)

    def test_remove_reasoning_content(self):
        # Test with no removal configured
        model = Model("gpt-4")
        text = "Here is <think>some reasoning</think> and regular text"
        self.assertEqual(model.remove_reasoning_content(text), text)

        # Test with removal configured
        model = Model("deepseek-r1")  # This model has remove_reasoning="think"
        text = """Here is some text
<think>
This is reasoning that should be removed
Over multiple lines
</think>
And more text here"""
        expected = """Here is some text

And more text here"""
        self.assertEqual(model.remove_reasoning_content(text), expected)

        # Test with multiple reasoning blocks
        text = """Start
<think>Block 1</think>
Middle
<think>Block 2</think>
End"""
        expected = """Start

Middle

End"""
        self.assertEqual(model.remove_reasoning_content(text), expected)

        # Test with no reasoning blocks
        text = "Just regular text"
        self.assertEqual(model.remove_reasoning_content(text), text)

    @patch("aider.models.litellm.completion")
    def test_simple_send_with_retries_removes_reasoning(self, mock_completion):
        model = Model("deepseek-r1")  # This model has remove_reasoning="think"

        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="""Here is some text
<think>
This reasoning should be removed
</think>
And this text should remain"""))]
        mock_completion.return_value = mock_response

        messages = [{"role": "user", "content": "test"}]
        result = model.simple_send_with_retries(messages)

        expected = """Here is some text

And this text should remain"""
        self.assertEqual(result, expected)

        # Verify the completion was called
        mock_completion.assert_called_once()

    def test_aider_extra_model_settings(self):
        import tempfile

        import yaml

        # Create temporary YAML file with test settings
        test_settings = [
            {
                "name": "aider/extra_params",
                "extra_params": {
                    "extra_headers": {"Foo": "bar"},
                    "some_param": "some value",
                },
            },
        ]

        # Write to a regular file instead of NamedTemporaryFile
        # for better cross-platform compatibility
        tmp = tempfile.mktemp(suffix=".yml")
        try:
            with open(tmp, "w") as f:
                yaml.dump(test_settings, f)

            # Register the test settings
            register_models([tmp])

            # Test that defaults are applied when no exact match
            model = Model("claude-3-5-sonnet-20240620")
            # Test that both the override and existing headers are present
            model = Model("claude-3-5-sonnet-20240620")
            self.assertEqual(model.extra_params["extra_headers"]["Foo"], "bar")
            self.assertEqual(
                model.extra_params["extra_headers"]["anthropic-beta"],
                ANTHROPIC_BETA_HEADER,
            )
            self.assertEqual(model.extra_params["some_param"], "some value")
            self.assertEqual(model.extra_params["max_tokens"], 8192)

            # Test that exact match overrides defaults but not overrides
            model = Model("gpt-4")
            self.assertEqual(model.extra_params["extra_headers"]["Foo"], "bar")
            self.assertEqual(model.extra_params["some_param"], "some value")
        finally:
            # Clean up the temporary file
            import os

            try:
                os.unlink(tmp)
            except OSError:
                pass

    @patch("aider.models.litellm.completion")
    @patch.object(Model, "token_count")
    def test_ollama_num_ctx_set_when_missing(self, mock_token_count, mock_completion):
        mock_token_count.return_value = 1000

        model = Model("ollama/llama3")
        messages = [{"role": "user", "content": "Hello"}]

        model.send_completion(messages, functions=None, stream=False)

        # Verify num_ctx was calculated and added to call
        expected_ctx = int(1000 * 1.25) + 8192  # 9442
        mock_completion.assert_called_once_with(
            model=model.name,
            messages=messages,
            stream=False,
            temperature=0,
            num_ctx=expected_ctx,
            timeout=600,
        )

    @patch("aider.models.litellm.completion")
    def test_ollama_uses_existing_num_ctx(self, mock_completion):
        model = Model("ollama/llama3")
        model.extra_params = {"num_ctx": 4096}

        messages = [{"role": "user", "content": "Hello"}]
        model.send_completion(messages, functions=None, stream=False)

        # Should use provided num_ctx from extra_params
        mock_completion.assert_called_once_with(
            model=model.name,
            messages=messages,
            stream=False,
            temperature=0,
            num_ctx=4096,
            timeout=600,
        )

    @patch("aider.models.litellm.completion")
    def test_non_ollama_no_num_ctx(self, mock_completion):
        model = Model("gpt-4")
        messages = [{"role": "user", "content": "Hello"}]

        model.send_completion(messages, functions=None, stream=False)

        # Regular models shouldn't get num_ctx
        mock_completion.assert_called_once_with(
            model=model.name,
            messages=messages,
            stream=False,
            temperature=0,
            timeout=600,
        )
        self.assertNotIn("num_ctx", mock_completion.call_args.kwargs)

    def test_use_temperature_settings(self):
        # Test use_temperature=True (default) uses temperature=0
        model = Model("gpt-4")
        self.assertTrue(model.use_temperature)
        self.assertEqual(model.use_temperature, True)

        # Test use_temperature=False doesn't pass temperature
        model = Model("github/o1-mini")
        self.assertFalse(model.use_temperature)

        # Test use_temperature as float value
        model = Model("gpt-4")
        model.use_temperature = 0.7
        self.assertEqual(model.use_temperature, 0.7)

    @patch("aider.models.litellm.completion")
    def test_request_timeout_default(self, mock_completion):
        # Test default timeout is used when not specified in extra_params
        model = Model("gpt-4")
        messages = [{"role": "user", "content": "Hello"}]
        model.send_completion(messages, functions=None, stream=False)
        mock_completion.assert_called_with(
            model=model.name,
            messages=messages,
            stream=False,
            temperature=0,
            timeout=600,  # Default timeout
        )

    @patch("aider.models.litellm.completion")
    def test_request_timeout_from_extra_params(self, mock_completion):
        # Test timeout from extra_params overrides default
        model = Model("gpt-4")
        model.extra_params = {"timeout": 300}  # 5 minutes
        messages = [{"role": "user", "content": "Hello"}]
        model.send_completion(messages, functions=None, stream=False)
        mock_completion.assert_called_with(
            model=model.name,
            messages=messages,
            stream=False,
            temperature=0,
            timeout=300,  # From extra_params
        )

    @patch("aider.models.litellm.completion")
    def test_use_temperature_in_send_completion(self, mock_completion):
        # Test use_temperature=True sends temperature=0
        model = Model("gpt-4")
        messages = [{"role": "user", "content": "Hello"}]
        model.send_completion(messages, functions=None, stream=False)
        mock_completion.assert_called_with(
            model=model.name,
            messages=messages,
            stream=False,
            temperature=0,
            timeout=600,
        )

        # Test use_temperature=False doesn't send temperature
        model = Model("github/o1-mini")
        messages = [{"role": "user", "content": "Hello"}]
        model.send_completion(messages, functions=None, stream=False)
        self.assertNotIn("temperature", mock_completion.call_args.kwargs)

        # Test use_temperature as float sends that value
        model = Model("gpt-4")
        model.use_temperature = 0.7
        messages = [{"role": "user", "content": "Hello"}]
        model.send_completion(messages, functions=None, stream=False)
        mock_completion.assert_called_with(
            model=model.name,
            messages=messages,
            stream=False,
            temperature=0.7,
            timeout=600,
        )


if __name__ == "__main__":
    unittest.main()
