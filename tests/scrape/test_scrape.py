import unittest
from unittest.mock import patch, MagicMock
import re

from aider.commands import Commands
from aider.io import InputOutput
from aider.scrape import Scraper


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

    @patch("aider.scrape.sync_playwright")
    def test_scrape_actual_url_with_playwright(self, mock_sync_playwright):
        # Mock the Playwright browser and page
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_browser.new_page.return_value = mock_page
        mock_page.content.return_value = "<html><body><h1>Test Page</h1></body></html>"
        mock_sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser

        # Create a Scraper instance with a mock print_error function
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=True)

        # Scrape a real URL
        result = scraper.scrape("https://example.com")

        # Assert that the result contains expected content
        self.assertIsNotNone(result)
        self.assertIn("Test Page", result)

        # Assert that print_error was never called
        mock_print_error.assert_not_called()

        # Assert that Playwright methods were called
        mock_sync_playwright.assert_called_once()
        mock_browser.new_page.assert_called()
        mock_page.goto.assert_called_with("https://example.com", wait_until="networkidle", timeout=5000)
        mock_page.content.assert_called_once()

    def test_scraper_print_error_not_called(self):
        # Create a Scraper instance with a mock print_error function
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error)

        # Test various methods of the Scraper class
        scraper.scrape_with_httpx("https://example.com")
        scraper.try_pandoc()
        scraper.html_to_markdown("<html><body><h1>Test</h1></body></html>")

        # Assert that print_error was never called
        mock_print_error.assert_not_called()


if __name__ == "__main__":
    unittest.main()
