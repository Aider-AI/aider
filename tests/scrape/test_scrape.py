import socket
import time
import unittest
from unittest.mock import MagicMock, patch

import httpcore
import httpx

from aider.commands import Commands
from aider.io import InputOutput
from aider.scrape import ScrapeNetworkBackend, Scraper


class TestScrape(unittest.TestCase):
    def test_scrape_self_signed_ssl(self):
        def scrape_with_retries(scraper, url, max_retries=5, delay=0.5):
            for _ in range(max_retries):
                result = scraper.scrape(url)
                if result is not None:
                    return result
                time.sleep(delay)
            return None

        # Test with SSL verification
        scraper_verify = Scraper(
            print_error=MagicMock(), playwright_available=True, verify_ssl=True
        )
        result_verify = scrape_with_retries(scraper_verify, "https://self-signed.badssl.com")
        self.assertIsNone(result_verify)
        scraper_verify.print_error.assert_called()

        # Test without SSL verification
        scraper_no_verify = Scraper(
            print_error=MagicMock(), playwright_available=True, verify_ssl=False
        )
        result_no_verify = scrape_with_retries(scraper_no_verify, "https://self-signed.badssl.com")
        self.assertIsNotNone(result_no_verify)
        self.assertIn("self-signed", result_no_verify)
        scraper_no_verify.print_error.assert_not_called()

    def setUp(self):
        self.io = InputOutput(yes=True)
        self.commands = Commands(self.io, None)

    def test_cmd_web_imports_playwright(self):
        # Create a mock print_error function
        mock_print_error = MagicMock()
        self.commands.io.tool_error = mock_print_error

        # Run the cmd_web command
        result = self.commands.cmd_web("https://example.com", return_content=True)

        # Assert that the result contains some content
        self.assertIsNotNone(result)
        self.assertNotEqual(result, "")

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

    def test_scrape_actual_url_with_playwright(self):
        # Create a Scraper instance with a mock print_error function
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=True)

        # Scrape a real URL
        result = scraper.scrape("https://example.com")

        # Assert that the result contains expected content
        self.assertIsNotNone(result)
        self.assertIn("Example Domain", result)

        # Assert that print_error was never called
        mock_print_error.assert_not_called()

    def test_scraper_print_error_not_called(self):
        # Create a Scraper instance with a mock print_error function
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, verify_ssl=False)

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

        # Mock the playwright module to raise an error
        import playwright

        playwright._impl._errors.Error = Exception  # Mock the Error class

        def mock_content():
            raise playwright._impl._errors.Error("Test error")

        # Mock the necessary objects and methods
        scraper.scrape_with_playwright = MagicMock()
        scraper.scrape_with_playwright.return_value = (None, None)

        # Call the scrape method
        result = scraper.scrape("https://93.184.216.34")

        # Assert that the result is None
        self.assertIsNone(result)

        # Assert that print_error was called with the expected error message
        mock_print_error.assert_called_once_with(
            "Failed to retrieve content from https://93.184.216.34"
        )

        # Reset the mock
        mock_print_error.reset_mock()

        # Test with a different return value
        scraper.scrape_with_playwright.return_value = ("Some content", "text/html")
        result = scraper.scrape("https://93.184.216.34")

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
        result = scraper.scrape("https://93.184.216.34")

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
        result = scraper.scrape("https://93.184.216.34")

        # Assert that the result is the expected markdown
        self.assertEqual(result, expected_markdown)

        # Assert that html_to_markdown was called with the HTML content
        scraper.html_to_markdown.assert_called_once_with(html_content)

    def test_scrape_blocks_private_urls_before_httpx(self):
        private_urls = [
            "http://10.0.0.1/",
            "http://127.0.0.1/",
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
            "http://[::1]/",
            "http://[fd00:ec2::254]/",
        ]

        for url in private_urls:
            with self.subTest(url=url):
                mock_print_error = MagicMock()
                scraper = Scraper(print_error=mock_print_error, playwright_available=False)
                scraper.scrape_with_httpx = MagicMock()

                result = scraper.scrape(url)

                self.assertIsNone(result)
                scraper.scrape_with_httpx.assert_not_called()
                mock_print_error.assert_called_once_with(
                    f"Blocked scraping private or metadata URL: {url}"
                )

    def test_scrape_blocks_private_urls_before_playwright(self):
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=True)
        scraper.scrape_with_playwright = MagicMock()

        result = scraper.scrape("http://192.168.1.10/docs")

        self.assertIsNone(result)
        scraper.scrape_with_playwright.assert_not_called()
        mock_print_error.assert_called_once_with(
            "Blocked scraping private or metadata URL: http://192.168.1.10/docs"
        )

    @patch("aider.scrape.socket.getaddrinfo")
    def test_scrape_blocks_metadata_hostname_without_dns(self, mock_getaddrinfo):
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=False)
        scraper.scrape_with_httpx = MagicMock()

        result = scraper.scrape("http://metadata.google.internal/computeMetadata/v1/")

        self.assertIsNone(result)
        mock_getaddrinfo.assert_not_called()
        scraper.scrape_with_httpx.assert_not_called()
        mock_print_error.assert_called_once_with(
            "Blocked scraping private or metadata URL: "
            "http://metadata.google.internal/computeMetadata/v1/"
        )

    @patch(
        "aider.scrape.socket.getaddrinfo",
        return_value=[(None, None, None, None, ("10.0.0.5", 80))],
    )
    def test_scrape_blocks_hostnames_that_resolve_private(self, mock_getaddrinfo):
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=False)
        scraper.scrape_with_httpx = MagicMock()

        result = scraper.scrape("https://docs.example.test/path")

        self.assertIsNone(result)
        mock_getaddrinfo.assert_called_once_with(
            "docs.example.test", 443, type=socket.SOCK_STREAM
        )
        scraper.scrape_with_httpx.assert_not_called()
        mock_print_error.assert_called_once_with(
            "Blocked scraping private or metadata URL: https://docs.example.test/path"
        )

    @patch(
        "aider.scrape.socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("224.0.0.1", 443))],
    )
    def test_scrape_blocks_hostnames_that_resolve_multicast(self, mock_getaddrinfo):
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=False)
        scraper.scrape_with_httpx = MagicMock()

        result = scraper.scrape("https://docs.example.test/path")

        self.assertIsNone(result)
        mock_getaddrinfo.assert_called_once_with(
            "docs.example.test", 443, type=socket.SOCK_STREAM
        )
        scraper.scrape_with_httpx.assert_not_called()
        mock_print_error.assert_called_once_with(
            "Blocked scraping private or metadata URL: https://docs.example.test/path"
        )

    @patch("aider.scrape.socket.getaddrinfo", side_effect=socket.gaierror("mock failure"))
    def test_scrape_blocks_unresolved_hostname_before_httpx(self, mock_getaddrinfo):
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=False)
        scraper.scrape_with_httpx = MagicMock()

        result = scraper.scrape("https://docs.example.test/path")

        self.assertIsNone(result)
        mock_getaddrinfo.assert_called_once_with(
            "docs.example.test", 443, type=socket.SOCK_STREAM
        )
        scraper.scrape_with_httpx.assert_not_called()
        mock_print_error.assert_called_once_with(
            "Unable to resolve URL host docs.example.test: mock failure"
        )

    def test_scrape_allows_public_ip_before_httpx(self):
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=False)
        scraper.scrape_with_httpx = MagicMock(return_value=("public content", "text/plain"))

        result = scraper.scrape("https://93.184.216.34/")

        self.assertEqual(result, "public content")
        scraper.scrape_with_httpx.assert_called_once_with("https://93.184.216.34/")
        mock_print_error.assert_not_called()

    def test_scrape_uses_httpx_for_hostnames_even_with_playwright(self):
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=True)
        scraper.scrape_with_playwright = MagicMock()
        scraper.scrape_with_httpx = MagicMock(return_value=("public content", "text/plain"))

        with patch(
            "aider.scrape.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
        ):
            result = scraper.scrape("https://docs.example.test/")

        self.assertEqual(result, "public content")
        scraper.scrape_with_playwright.assert_not_called()
        scraper.scrape_with_httpx.assert_called_once_with("https://docs.example.test/")
        mock_print_error.assert_not_called()

    def test_httpx_backend_blocks_dns_rebinding_at_connect_time(self):
        mock_print_error = MagicMock()
        scraper = Scraper(print_error=mock_print_error, playwright_available=False)
        safe_addresses = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, ("93.184.216.34", 443), "93.184.216.34")
        ]
        scraper.get_safe_addresses = MagicMock(
            side_effect=[
                (safe_addresses, None),
                ([], "Blocked scraping private or metadata URL: docs.example.test:443"),
            ]
        )

        result = scraper.scrape_with_httpx("https://docs.example.test/")

        self.assertEqual(scraper.get_safe_addresses.call_count, 2)
        self.assertIsNone(result[0])
        mock_print_error.assert_called_once_with(
            "HTTP error occurred: Blocked scraping private or metadata URL: "
            "docs.example.test:443"
        )

    def test_httpx_network_backend_connects_to_validated_address(self):
        scraper = Scraper(print_error=MagicMock(), playwright_available=False)
        backend = ScrapeNetworkBackend(scraper)
        sock = MagicMock()
        getaddrinfo_result = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ]

        with patch("aider.scrape.socket.getaddrinfo", return_value=getaddrinfo_result):
            with patch("aider.scrape.socket.socket", return_value=sock):
                backend.connect_tcp("docs.example.test", 443)

        sock.connect.assert_called_once_with(("93.184.216.34", 443))

    @patch(
        "aider.scrape.socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))],
    )
    def test_httpx_network_backend_rejects_private_connect_address(self, mock_getaddrinfo):
        scraper = Scraper(print_error=MagicMock(), playwright_available=False)
        backend = ScrapeNetworkBackend(scraper)

        with patch("aider.scrape.socket.socket") as mock_socket:
            with self.assertRaises(httpcore.ConnectError):
                backend.connect_tcp("docs.example.test", 443)

        mock_getaddrinfo.assert_called_once_with(
            "docs.example.test", 443, type=socket.SOCK_STREAM
        )
        mock_socket.assert_not_called()

    @patch("httpx.Client")
    def test_scrape_blocks_private_redirect_before_following(self, mock_client_class):
        mock_print_error = MagicMock()
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None
        mock_client_class.return_value = client
        client.get.return_value = httpx.Response(
            302,
            headers={"location": "http://169.254.169.254/latest/meta-data/"},
            request=httpx.Request("GET", "https://93.184.216.34/start"),
        )
        scraper = Scraper(print_error=mock_print_error, playwright_available=False)

        result = scraper.scrape("https://93.184.216.34/start")

        self.assertIsNone(result)
        client.get.assert_called_once_with("https://93.184.216.34/start")
        mock_print_error.assert_any_call(
            "Blocked scraping private or metadata URL: "
            "http://169.254.169.254/latest/meta-data/"
        )

    def test_playwright_route_blocks_private_request(self):
        scraper = Scraper(print_error=MagicMock(), playwright_available=True)
        route = MagicMock()
        route.request.url = "http://169.254.169.254/latest/meta-data/"

        scraper.route_scrape_request(route)

        route.abort.assert_called_once()
        route.continue_.assert_not_called()
        self.assertEqual(
            scraper._blocked_playwright_request_error,
            "Blocked scraping private or metadata URL: "
            "http://169.254.169.254/latest/meta-data/",
        )

    def test_playwright_route_allows_public_request(self):
        scraper = Scraper(print_error=MagicMock(), playwright_available=True)
        route = MagicMock()
        route.request.url = "https://93.184.216.34/"

        scraper.route_scrape_request(route)

        route.continue_.assert_called_once()
        route.abort.assert_not_called()
        self.assertIsNone(scraper._blocked_playwright_request_error)

    def test_playwright_route_blocks_hostname_request(self):
        scraper = Scraper(print_error=MagicMock(), playwright_available=True)
        route = MagicMock()
        route.request.url = "https://docs.example.test/"

        with patch(
            "aider.scrape.socket.getaddrinfo",
            return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
        ):
            scraper.route_scrape_request(route)

        route.abort.assert_called_once()
        route.continue_.assert_not_called()
        self.assertEqual(
            scraper._blocked_playwright_request_error,
            "Blocked scraping browser URL that requires DNS resolution: "
            "https://docs.example.test/",
        )


if __name__ == "__main__":
    unittest.main()
