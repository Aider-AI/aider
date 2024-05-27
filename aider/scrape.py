#!/usr/bin/env python

import re
import sys

import httpx
import pypandoc
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from aider import __version__

aider_user_agent = f"Aider/{__version__} +https://aider.chat"

# Playwright is nice because it has a simple way to install dependencies on most
# platforms.
PLAYWRIGHT_INFO = """
For better web scraping, install Playwright chromium with this command in your terminal:

    playwright install --with-deps chromium

See https://aider.chat/docs/install.html#enable-playwright-optional for more info.
"""


class Scraper:
    pandoc_available: bool | None = None
    playwright_available: bool | None = None
    playwright_instructions_shown: bool = False

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
        # content = html_to_text(content)

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
            page.goto(url)
            content = page.content()
            browser.close()

        return content

    def try_playwright(self):
        if self.playwright_available is not None:
            return

        with sync_playwright() as p:
            try:
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


# Adapted from AutoGPT, MIT License
#
# https://github.com/Significant-Gravitas/AutoGPT/blob/fe0923ba6c9abb42ac4df79da580e8a4391e0418/autogpts/autogpt/autogpt/commands/web_selenium.py#L173


def html_to_text(page_source: str) -> str:
    soup = BeautifulSoup(page_source, "html.parser")

    for script in soup(["script", "style"]):
        script.extract()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)
    return text


def main(url):
    scraper = Scraper()
    content = scraper.scrape(url)
    print(content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playw.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
