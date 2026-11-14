import unittest

from aider.args import get_parser
from aider.format_settings import format_settings, scrub_sensitive_info


class TestScrubSensitiveInfo(unittest.TestCase):
    def setUp(self):
        self.parser = get_parser([], None)

    def parse(self, argv):
        return self.parser.parse_args(argv)

    def test_scrubs_dedicated_api_key_options(self):
        args = self.parse(
            ["--openai-api-key", "sk-openai-secret-1234", "--anthropic-api-key", "sk-ant-secret"]
        )
        text = "aider --openai-api-key sk-openai-secret-1234 --anthropic-api-key sk-ant-secret"
        self.assertEqual(
            scrub_sensitive_info(args, text),
            "aider --openai-api-key ...1234 --anthropic-api-key ...cret",
        )

    def test_scrubs_generic_api_key_option(self):
        args = self.parse(["--api-key", "deepseek=sk-deep-secret-987654"])
        text = "aider --api-key deepseek=sk-deep-secret-987654"
        self.assertEqual(
            scrub_sensitive_info(args, text),
            "aider --api-key deepseek=...7654",
        )

    def test_scrubs_secret_set_env_option(self):
        args = self.parse(["--set-env", "GEMINI_API_KEY=AIza-secret-112233"])
        text = "aider --set-env GEMINI_API_KEY=AIza-secret-112233"
        self.assertEqual(
            scrub_sensitive_info(args, text),
            "aider --set-env GEMINI_API_KEY=...2233",
        )

    def test_keeps_plain_set_env_option(self):
        args = self.parse(["--set-env", "OPENAI_API_BASE=https://example.test/v1"])
        text = "aider --set-env OPENAI_API_BASE=https://example.test/v1"
        self.assertEqual(scrub_sensitive_info(args, text), text)

    def test_format_settings_hides_all_credentials(self):
        args = self.parse(
            [
                "--api-key",
                "deepseek=sk-deep-secret-987654",
                "--set-env",
                "GEMINI_API_KEY=AIza-secret-112233",
            ]
        )
        show = format_settings(self.parser, args)

        self.assertNotIn("sk-deep-secret-987654", show)
        self.assertNotIn("AIza-secret-112233", show)
        self.assertIn("...7654", show)
        self.assertIn("...2233", show)

    def test_scrub_tolerates_missing_args(self):
        self.assertEqual(scrub_sensitive_info(self.parse([]), "plain text"), "plain text")
        self.assertIsNone(scrub_sensitive_info(self.parse([]), None))


if __name__ == "__main__":
    unittest.main()
