import unittest
from unittest.mock import ANY, MagicMock, patch

from aider.models import (
    ANTHROPIC_BETA_HEADER,
    Model,
    ModelInfoManager,
    ModelSettings,
    get_model_settings,
    register_models,
    sanity_check_model,
    sanity_check_models,
)


class TestModels(unittest.TestCase):
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
        self.assertEqual(model.name, "openai/gpt-4-0613")

        model = Model("4o")
        self.assertEqual(model.name, "openai/gpt-4o")

        model = Model("35turbo")
        self.assertEqual(model.name, "openai/gpt-3.5-turbo")

        model = Model("35-turbo")
        self.assertEqual(model.name, "openai/gpt-3.5-turbo")

        model = Model("3")
        self.assertEqual(model.name, "openai/gpt-3.5-turbo")

        model = Model("sonnet")
        self.assertEqual(model.name, "anthropic/claude-3-5-sonnet-20241022")

        model = Model("haiku")
        self.assertEqual(model.name, "anthropic/claude-3-5-haiku-20241022")

        model = Model("opus")
        self.assertEqual(model.name, "anthropic/claude-3-opus-20240229")

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

    def test_get_model_settings_with_or_without_prefix(self):
        # Test that get_model_settings returns same settings with or without prefix
        settings_with_prefix = get_model_settings("openai/gpt-4o")
        settings_without_prefix = get_model_settings("gpt-4o")

        self.assertIsInstance(settings_with_prefix, ModelSettings)
        self.assertEqual(settings_with_prefix, settings_without_prefix)

        # Test with a different model to verify behavior
        settings_with_prefix = get_model_settings("anthropic/claude-3-opus-20240229")
        settings_without_prefix = get_model_settings("claude-3-opus-20240229")

        self.assertIsInstance(settings_with_prefix, ModelSettings)
        self.assertEqual(settings_with_prefix, settings_without_prefix)

    def test_get_model_settings_invalid(self):
        # Test that get_model_settings returns None for invalid model names
        self.assertIsNone(get_model_settings("invalid-model-name"))
        self.assertIsNone(get_model_settings("openai/invalid-model"))
        self.assertIsNone(get_model_settings("not-a-provider/gpt-4"))

    def test_weak_model_settings(self):
        # When weak_model is None and no weak model configured, use self
        model = Model("openai/gpt-undefined", weak_model_name=None)
        self.assertIs(model.weak_model, model)

        # When weak_model is None and model has weak model configured
        model = Model("openai/gpt-4o", weak_model_name=None)
        self.assertEqual(model.weak_model.name, model.weak_model_name)

        # Test when weak_model is False
        model = Model("openai/gpt-4o", weak_model_name=False)
        self.assertIsNone(model.weak_model)

        # Test when weak_model_name matches model name
        model = Model("openai/gpt-undefined", weak_model_name="openai/gpt-undefined")
        self.assertIs(model.weak_model, model)

        # Test when weak_model_name is different, and none configured
        model = Model("openai/gpt-undefined", weak_model_name="gpt-3.5-turbo")
        self.assertNotEqual(model.weak_model, model)
        self.assertEqual(model.weak_model.name, "openai/gpt-3.5-turbo")

        # Test when weak_model_name is different, and other configured
        model = Model("openai/gpt-4o", weak_model_name="gpt-3.5-turbo")
        self.assertNotEqual(model.weak_model, model)
        self.assertEqual(model.weak_model.name, "openai/gpt-3.5-turbo")

    def test_editor_model_settings(self):
        # Test when model has no editor model configured, use self
        model = Model("openai/gpt-undefined", editor_model_name=None)
        self.assertIs(model.editor_model, model)

        # Test when model has editor model configured
        model = Model("anthropic/claude-3-5-sonnet-20240620")
        self.assertEqual(model.editor_model.name, "anthropic/claude-3-5-sonnet-20240620")
        self.assertIs(model.editor_model, model)

        # Test when editor_model is False
        model = Model("anthropic/claude-3-5-sonnet-20240620", editor_model_name=False)
        self.assertIsNone(model.editor_model)

        # Test when editor_model_name matches model name
        model = Model("openai/gpt-4o", editor_model_name="openai/gpt-4o")
        self.assertIs(model.editor_model, model)

    def test_editor_edit_format(self):
        # Test when editor_edit_format is provided, override the model settings
        model = Model("openai/gpt-4o", editor_edit_format="whole")
        self.assertEqual(model.editor_edit_format, "whole")

        # Test when editor_edit_format is not provided, use the model settings
        model = Model("openai/gpt-4o")
        self.assertEqual(model.editor_edit_format, "editor-diff")

        # Test when editor_model_name is provided, use the model settings
        model = Model("openai/gpt-4o", editor_model_name="openai/gpt-4o")
        self.assertEqual(model.editor_edit_format, "editor-diff")

        # When editor_model_name and editor_edit_format is provided, overrides the model settings
        model = Model(
            "openai/gpt-4o", editor_model_name="openai/gpt-4o", editor_edit_format="whole"
        )
        self.assertEqual(model.editor_edit_format, "whole")

        # When model editor_edit_format is not specified, use the editor_model settings
        model = Model("openai/gpt-4-turbo", editor_model_name="openai/gpt-4o")
        self.assertEqual(model.editor_edit_format, "diff")

        # When editor_model_name=False, ignore provided editor_edit_format
        model = Model("openai/gpt-4-turbo", editor_model_name=False, editor_edit_format="whole")
        self.assertIsNone(model.editor_edit_format)


if __name__ == "__main__":
    unittest.main()
