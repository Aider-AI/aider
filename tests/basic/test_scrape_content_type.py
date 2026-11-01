import unittest
from unittest.mock import MagicMock, patch

import httpx

from aider.scrape import Scraper


class TestScrapeContentType(unittest.TestCase):
    def test_httpx_content_type(self):
        html = "<html><body><h1>Hello</h1></body></html>"
        cases = [
            ({}, html, True),
            ({"content-type": ""}, html, True),
            ({"content-type": "text/plain"}, html, False),
            ({"content-type": "text/html; charset=utf-8"}, html, True),
            ({}, "ordinary text", False),
        ]
        for headers, content, should_convert in cases:
            with self.subTest(headers=headers, content=content):
                response = httpx.Response(
                    200,
                    headers=headers,
                    content=content.encode("utf-8"),
                    request=httpx.Request("GET", "https://example.com"),
                )
                scraper = Scraper(playwright_available=False)
                scraper.try_pandoc = MagicMock()
                scraper.html_to_markdown = MagicMock(return_value="# Hello")
                with patch("httpx.Client") as client:
                    client.return_value.__enter__.return_value.get.return_value = response
                    result = scraper.scrape("https://example.com")
                self.assertEqual(result, "# Hello" if should_convert else content)
                self.assertEqual(scraper.html_to_markdown.called, should_convert)
