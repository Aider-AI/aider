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
        self.assertEqual(model.name, "gpt-4o-2024-08-06")

        model = Model("35turbo")
        self.assertEqual(model.name, "gpt-3.5-turbo")

        model = Model("35-turbo")
        self.assertEqual(model.name, "gpt-3.5-turbo")

        model = Model("3")
        self.assertEqual(model.name, "gpt-3.5-turbo")

        model = Model("sonnet")
        self.assertEqual(model.name, "claude-3-sonnet-20241022")

        model = Model("haiku")
        self.assertEqual(model.name, "claude-3-haiku-20241022")

        model = Model("opus")
        self.assertEqual(model.name, "claude-3-opus-20240229")

        # Test non-alias passes through unchanged
        model = Model("gpt-4")
        self.assertEqual(model.name, "gpt-4")

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


if __name__ == "__main__":
    unittest.main()
