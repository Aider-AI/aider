import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from aider.scrape import Scraper


class TestPlaywrightPlainText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = 'first line\n<example> & "quoted"\n你好\n'

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                content_type = "text/plain; charset=utf-8"
                body = cls.content.encode("utf-8")
                if self.path == "/page.html":
                    content_type = "text/html; charset=utf-8"
                    body = (
                        b'<html><body><p id="result"></p>'
                        b'<script>document.getElementById("result").textContent = '
                        b'"rendered content";</script></body></html>'
                    )
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/example.txt"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_plain_text_matches_http_response(self):
        scraper = Scraper(playwright_available=True)
        self.assertEqual(scraper.scrape(self.url), self.content)

    def test_httpx_plain_text_control(self):
        scraper = Scraper(playwright_available=False)
        self.assertEqual(scraper.scrape(self.url), self.content)

    def test_html_still_uses_rendered_dom(self):
        scraper = Scraper(playwright_available=True)
        url = f"http://127.0.0.1:{self.server.server_port}/page.html"
        content, mime_type = scraper.scrape_with_playwright(url)
        self.assertEqual(mime_type, "text/html")
        self.assertIn('<p id="result">rendered content</p>', content)
