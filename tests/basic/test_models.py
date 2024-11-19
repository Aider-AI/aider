import unittest
from unittest.mock import ANY, MagicMock, call, patch

from aider.models import (
    MODEL_SETTINGS,
    Model,
    ModelInfoManager,
    ModelSettings,
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

        warning_messages = [warning_call.args[0] for warning_call in mock_io.tool_warning.call_args_list]
        print("Warning messages:", warning_messages)  # Add this line

        self.assertGreaterEqual(mock_io.tool_warning.call_count, 1)  # Expect two warnings
        self.assertTrue(
            any("bogus-model" in msg for msg in warning_messages)
        )  # Check that one of the warnings mentions the bogus model

    def test_default_and_override_settings(self):
        import tempfile
        import yaml

        # Create temporary YAML file with test settings
        test_settings = [
            {
                "name": "aider/default",
                "edit_format": "fake",
                "use_repo_map": True,
            },
            {
                "name": "aider/override",
                "use_temperature": False,
            }
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml') as tmp:
            yaml.dump(test_settings, tmp)
            tmp.flush()
            
            # Register the test settings
            register_models([tmp.name])

            # Test that defaults are applied when no exact match
            model = Model("unknown-model")
            self.assertEqual(model.edit_format, "fake")
            self.assertTrue(model.use_repo_map)
            self.assertFalse(model.use_temperature)  # Override should win

            # Test that exact match overrides defaults but not overrides
            model = Model("gpt-4")
            self.assertNotEqual(model.edit_format, "fake")  # Model setting should win over default
            self.assertFalse(model.use_temperature)  # Override should still win

            # Clean up by removing test settings
            MODEL_SETTINGS[:] = [
                ms for ms in MODEL_SETTINGS if ms.name not in ("aider/default", "aider/override")
            ]


if __name__ == "__main__":
    unittest.main()
