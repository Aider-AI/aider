import sys
import unittest
from unittest.mock import MagicMock, patch

from aider.commands import Commands
from aider.io import InputOutput
from aider.scrape import Scraper


class TestScrape(unittest.TestCase):
    @patch("aider.scrape.Scraper.scrape_with_httpx")
    @patch("aider.scrape.Scraper.scrape_with_playwright")
    def test_scrape_self_signed_ssl(self, mock_scrape_playwright, mock_scrape_httpx):
        # Test with SSL verification - playwright fails
        mock_scrape_playwright.return_value = (None, None)

        scraper_verify = Scraper(
            print_error=MagicMock(), playwright_available=True, verify_ssl=True
        )
        result_verify = scraper_verify.scrape("https://self-signed.badssl.com")
        self.assertIsNone(result_verify)
        scraper_verify.print_error.assert_called()

        # Test without SSL verification - playwright succeeds
        mock_scrape_playwright.return_value = (
            "<html><body>self-signed content</body></html>",
            "text/html",
        )
        scraper_no_verify = Scraper(
            print_error=MagicMock(), playwright_available=True, verify_ssl=False
        )
        result_no_verify = scraper_no_verify.scrape("https://self-signed.badssl.com")
        self.assertIsNotNone(result_no_verify)
        self.assertIn("self-signed", result_no_verify)
        scraper_no_verify.print_error.assert_not_called()

    def setUp(self):
        self.io = InputOutput(yes=True)
        self.commands = Commands(self.io, None)

    @patch("aider.commands.install_playwright")
    @patch("aider.commands.Scraper")
    def test_cmd_web_imports_playwright(self, mock_scraper_class, mock_install_playwright):
        # Since install_playwright is mocked, we need to simulate its side effect
        # of making the playwright module importable.
        def mock_install(*args, **kwargs):
            sys.modules["playwright"] = MagicMock()
            return True

        mock_install_playwright.side_effect = mock_install

        mock_scraper_instance = mock_scraper_class.return_value
        mock_scraper_instance.scrape.return_value = "Scraped content"

        # Create a mock print_error function
        mock_print_error = MagicMock()
        self.commands.io.tool_error = mock_print_error

        try:
            # Run the cmd_web command
            result = self.commands.cmd_web("https://example.com", return_content=True)

            # Assert that the result contains some content
            self.assertIsNotNone(result)
            self.assertIn("Scraped content", result)

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

            # Assert that print_error was never called
            mock_print_error.assert_not_called()
        finally:
            # Clean up sys.modules to avoid side effects on other tests
            if "playwright" in sys.modules:
                del sys.modules["playwright"]

    @patch("aider.scrape.Scraper.scrape_with_playwright")
    def test_scrape_actual_url_with_playwright(self, mock_scrape_playwright):
        # Create a Scraper instance with a mock print_error function
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=True)

        # Mock the playwright scrape to return content
        mock_scrape_playwright.return_value = (
            "<html><body><h1>Example Domain</h1></body></html>",
            "text/html",
        )

        # Scrape a mocked URL
        result = scraper.scrape("https://example.com")

        # Assert that the result contains expected content
        self.assertIsNotNone(result)
        self.assertIn("Example Domain", result)

        # Assert that print_error was never called
        mock_print_error.assert_not_called()

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

    def test_scrape_with_playwright_error_handling(self):
        # Create a Scraper instance with a mock print_error function
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=True)

        # Mock the necessary objects and methods
        scraper.scrape_with_playwright = MagicMock()
        scraper.scrape_with_playwright.return_value = (None, None)

        # Call the scrape method
        result = scraper.scrape("https://example.com")

        # Assert that the result is None
        self.assertIsNone(result)

        # Assert that print_error was called with the expected error message
        mock_print_error.assert_called_once_with(
            "Failed to retrieve content from https://example.com"
        )

        # Reset the mock
        mock_print_error.reset_mock()

        # Test with a different return value
        scraper.scrape_with_playwright.return_value = ("Some content", "text/html")
        result = scraper.scrape("https://example.com")

        # Assert that the result is not None
        self.assertIsNotNone(result)

        # Assert that print_error was not called
        mock_print_error.assert_not_called()

    def test_scrape_text_plain(self):
        # Create a Scraper instance
        scraper = Scraper(print_error=MagicMock(), playwright_available=True)

        # Mock the scrape_with_playwright method
        plain_text = "This is plain text content."
        scraper.scrape_with_playwright = MagicMock(return_value=(plain_text, "text/plain"))

        # Call the scrape method
        result = scraper.scrape("https://example.com")

        # Assert that the result is the same as the input plain text
        self.assertEqual(result, plain_text)

    def test_scrape_text_html(self):
        # Create a Scraper instance
        scraper = Scraper(print_error=MagicMock(), playwright_available=True)

        # Mock the scrape_with_playwright method
        html_content = "<html><body><h1>Test</h1><p>This is HTML content.</p></body></html>"
        scraper.scrape_with_playwright = MagicMock(return_value=(html_content, "text/html"))

        # Mock the html_to_markdown method
        expected_markdown = "# Test\n\nThis is HTML content."
        scraper.html_to_markdown = MagicMock(return_value=expected_markdown)

        # Call the scrape method
        result = scraper.scrape("https://example.com")

        # Assert that the result is the expected markdown
        self.assertEqual(result, expected_markdown)

        # Assert that html_to_markdown was called with the HTML content
        scraper.html_to_markdown.assert_called_once_with(html_content)


if __name__ == "__main__":
    unittest.main()
