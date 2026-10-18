import os
import unittest
from unittest.mock import patch

from aider import acedatacloud
from aider.models import Model, ModelInfoManager, fuzzy_match_models


class TestAceDataCloud(unittest.TestCase):
    def test_explicit_provider_preserves_model_id(self):
        self.assertEqual(acedatacloud.transport_model("acedatacloud/gpt-4.1"), "openai/gpt-4.1")
        self.assertEqual(acedatacloud.transport_model("openai/gpt-4.1"), "openai/gpt-4.1")
        with self.assertRaises(ValueError):
            acedatacloud.transport_model("acedatacloud/")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "unrelated"}, clear=True)
    def test_openai_key_does_not_authorize_ace(self):
        result = acedatacloud.validate_environment()
        self.assertFalse(result["keys_in_environment"])
        self.assertEqual(result["missing_keys"], ["ACEDATACLOUD_API_KEY"])
        with self.assertRaisesRegex(ValueError, "ACEDATACLOUD_API_KEY"):
            acedatacloud.completion_kwargs("acedatacloud/gpt-4.1")

    @patch.dict(os.environ, {"ACEDATACLOUD_API_KEY": "  "}, clear=True)
    def test_empty_key_is_missing(self):
        self.assertFalse(acedatacloud.validate_environment()["keys_in_environment"])

    @patch.dict(os.environ, {"ACEDATACLOUD_API_KEY": "ace-fixture-only"}, clear=True)
    def test_native_model_settings_and_no_auxiliary_model(self):
        model = Model("acedatacloud/gpt-4.1")
        self.assertEqual(model.name, "acedatacloud/gpt-4.1")
        self.assertEqual(model.edit_format, "diff")
        self.assertIs(model.weak_model, model)
        self.assertIs(model.editor_model, model)
        self.assertEqual(model.info, {})

    def test_metadata_does_not_copy_other_provider_price(self):
        manager = ModelInfoManager()
        with patch.object(manager, "_load_cache") as load:
            self.assertEqual(manager.get_model_info("acedatacloud/gpt-4.1"), {})
            load.assert_not_called()
        manager.local_model_metadata["acedatacloud/gpt-4.1"] = {"max_input_tokens": 1234}
        self.assertEqual(manager.get_model_info("acedatacloud/gpt-4.1"), {"max_input_tokens": 1234})

    @patch.dict(
        os.environ,
        {
            "ACEDATACLOUD_API_KEY": "ace-fixture-only",
            "OPENAI_API_KEY": "unrelated",
            "OPENAI_API_BASE": "https://unrelated.invalid/v1",
            "GITHUB_COPILOT_TOKEN": "unrelated-copilot",
        },
        clear=True,
    )
    def test_transport_is_provider_scoped_and_key_is_not_logged(self):
        model = Model("acedatacloud/gpt-4.1", verbose=True)
        model.extra_params = {"api_base": "https://unrelated.invalid", "max_tokens": 128}
        with (
            patch("aider.models.litellm.completion") as completion,
            patch("aider.models.dump") as dump,
            patch.object(model, "github_copilot_token_to_open_ai_key") as copilot,
        ):
            model.send_completion([{"role": "user", "content": "fixture"}], None, True)
            call = completion.call_args.kwargs
            self.assertEqual(call["model"], "openai/gpt-4.1")
            self.assertEqual(call["api_base"], "https://api.acedata.cloud/v1")
            self.assertEqual(call["api_key"], "ace-fixture-only")
            self.assertEqual(call["custom_llm_provider"], "openai")
            self.assertTrue(call["stream"])
            self.assertEqual(call["max_tokens"], 128)
            self.assertTrue(dump.called)
            copilot.assert_not_called()
        self.assertEqual(os.environ["OPENAI_API_KEY"], "unrelated")
        self.assertEqual(os.environ["OPENAI_API_BASE"], "https://unrelated.invalid/v1")

    @patch.dict(os.environ, {"ACEDATACLOUD_API_KEY": "ace-fixture-only"}, clear=True)
    def test_verbose_output_does_not_contain_dedicated_key(self):
        model = Model("acedatacloud/gpt-4.1", verbose=True)
        snapshots = []
        with (
            patch("aider.models.litellm.completion"),
            patch("aider.models.dump", side_effect=lambda kwargs: snapshots.append(dict(kwargs))),
        ):
            model.send_completion([{"role": "user", "content": "fixture"}], None, False)
        self.assertNotIn("ace-fixture-only", repr(snapshots))

    @patch.dict(os.environ, {"ACEDATACLOUD_API_KEY": "ace-fixture-only"}, clear=True)
    def test_token_counter_uses_chat_transport(self):
        model = Model("acedatacloud/gpt-4.1")
        with patch("aider.models.litellm.token_counter", return_value=12) as count:
            self.assertEqual(model.token_count([{"role": "user", "content": "fixture"}]), 12)
            self.assertEqual(count.call_args.kwargs["model"], "openai/gpt-4.1")

    def test_model_search_discovers_provider_preset(self):
        with patch("aider.models.litellm.model_cost", {}):
            self.assertIn("acedatacloud/gpt-4.1", fuzzy_match_models("acedatacloud/"))

    @patch.dict(os.environ, {"ACEDATACLOUD_API_KEY": "ace-fixture-only"}, clear=True)
    def test_key_only_start_requires_explicit_model_without_oauth(self):
        from argparse import Namespace
        from unittest.mock import MagicMock

        from aider.onboarding import select_default_model

        io = MagicMock()
        with patch("aider.onboarding.offer_openrouter_oauth") as oauth:
            self.assertIsNone(select_default_model(Namespace(model=None), io, MagicMock()))
            oauth.assert_not_called()
        self.assertIn("acedatacloud/<model>", io.tool_warning.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
