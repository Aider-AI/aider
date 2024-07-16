import unittest
from unittest.mock import patch

from aider.commands import Commands
from aider.io import InputOutput


class TestScrape(unittest.TestCase):
    def setUp(self):
        self.io = InputOutput(yes=True)
        self.commands = Commands(self.io, None)

    @patch("aider.scrape.Scraper.scrape")
    def test_cmd_web_imports_playwright(self, mock_scrape):
        # Mock the scrape method
        mock_scrape.return_value = "Mocked webpage content"

        # Run the cmd_web command
        result = self.commands.cmd_web("https://example.com")

        # Assert that the scrape method was called with the correct URL
        mock_scrape.assert_called_once_with("https://example.com")

        # Assert that the result contains the mocked content
        self.assertIn("Mocked webpage content", result)

        # Try to import playwright
        try:
            import playwright  # noqa: F401

            playwright_imported = True
        except ImportError:
            playwright_imported = False

        # Assert that playwright was successfully imported
        self.assertTrue(
            playwright_imported, "Playwright should be importable after running cmd_web"
        )


if __name__ == "__main__":
    unittest.main()
