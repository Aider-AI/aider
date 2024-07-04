#!/usr/bin/env python

import re
import sys

import playwright
import pypandoc
from playwright.sync_api import sync_playwright

from aider import __version__, urls
from aider.dump import dump  # noqa: F401

aider_user_agent = f"Aider/{__version__} +{urls.website}"

# Playwright is nice because it has a simple way to install dependencies on most
# platforms.
PLAYWRIGHT_INFO = f"""
For better web scraping, install Playwright chromium with this command in your terminal:

    playwright install --with-deps chromium

See {urls.enable_playwright} for more info.
"""


class Scraper:
    pandoc_available = None
    playwright_available = None
    playwright_instructions_shown = False

    # Public API...
    def __init__(self, print_error=None):
        """
        `print_error` - a function to call to print error/debug info.
        """
        if print_error:
            self.print_error = print_error
        else:
            self.print_error = print

    def scrape(self, url):
        """
        Scrape a url and turn it into readable markdown.

        `url` - the URLto scrape.
        """
        self.try_playwright()

        if self.playwright_available:
            content = self.scrape_with_playwright(url)
        else:
            content = self.scrape_with_httpx(url)

        if not content:
            return

        self.try_pandoc()

        content = self.html_to_markdown(content)

        return content

    # Internals...
    def scrape_with_playwright(self, url):
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:
                self.playwright_available = False
                self.print_error(e)
                return

            page = browser.new_page()

            user_agent = page.evaluate("navigator.userAgent")
            user_agent = user_agent.replace("Headless", "")
            user_agent = user_agent.replace("headless", "")
            user_agent += " " + aider_user_agent

            page = browser.new_page(user_agent=user_agent)
            try:
                page.goto(url, wait_until="networkidle", timeout=5000)
            except playwright._impl._errors.TimeoutError:
                pass
            content = page.content()
            browser.close()

        return content

    def try_playwright(self):
        if self.playwright_available is not None:
            return

        try:
            with sync_playwright() as p:
                p.chromium.launch()
                self.playwright_available = True
        except Exception:
            self.playwright_available = False

    def get_playwright_instructions(self):
        if self.playwright_available in (True, None):
            return
        if self.playwright_instructions_shown:
            return

        self.playwright_instructions_shown = True
        return PLAYWRIGHT_INFO

    def scrape_with_httpx(self, url):
        import httpx

        headers = {"User-Agent": f"Mozilla./5.0 ({aider_user_agent})"}
        try:
            with httpx.Client(headers=headers) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as http_err:
            self.print_error(f"HTTP error occurred: {http_err}")
        except Exception as err:
            self.print_error(f"An error occurred: {err}")
        return None

    def try_pandoc(self):
        if self.pandoc_available:
            return

        try:
            pypandoc.get_pandoc_version()
            self.pandoc_available = True
            return
        except OSError:
            pass

        pypandoc.download_pandoc(delete_installer=True)
        self.pandoc_available = True

    def html_to_markdown(self, page_source):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(page_source, "html.parser")
        soup = slimdown_html(soup)
        page_source = str(soup)

        md = pypandoc.convert_text(page_source, "markdown", format="html")

        md = re.sub(r"</div>", "      ", md)
        md = re.sub(r"<div>", "     ", md)

        md = re.sub(r"\n\s*\n", "\n\n", md)

        return md


def slimdown_html(soup):
    for svg in soup.find_all("svg"):
        svg.decompose()

    if soup.img:
        soup.img.decompose()

    for tag in soup.find_all(href=lambda x: x and x.startswith("data:")):
        tag.decompose()

    for tag in soup.find_all(src=lambda x: x and x.startswith("data:")):
        tag.decompose()

    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr != "href":
                tag.attrs.pop(attr, None)

    return soup


def main(url):
    scraper = Scraper()
    content = scraper.scrape(url)
    print(content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playw.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
