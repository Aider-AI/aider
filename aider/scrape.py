#!/usr/bin/env python

import re
import sys

import pypandoc

from aider import __version__, urls, utils
from aider.dump import dump  # noqa: F401

aider_user_agent = f"Aider/{__version__} +{urls.website}"

# Playwright is nice because it has a simple way to install dependencies on most
# platforms.


def install_playwright(io):
    try:
        from playwright.sync_api import sync_playwright

        has_pip = True
    except ImportError:
        has_pip = False

    try:
        with sync_playwright() as p:
            p.chromium.launch()
            has_chromium = True
    except Exception:
        has_chromium = False

    if has_pip and has_chromium:
        return True

    pip_cmd = utils.get_pip_install(["aider-chat[playwright]"])
    chromium_cmd = "-m playwright install --with-deps chromium"
    chromium_cmd = [sys.executable] + chromium_cmd.split()

    cmds = ""
    if not has_pip:
        cmds += " ".join(pip_cmd) + "\n"
    if not has_chromium:
        cmds += " ".join(chromium_cmd) + "\n"

    text = f"""For the best web scraping, install Playwright:

{cmds}
See {urls.enable_playwright} for more info.
"""

    io.tool_output(text)
    if not io.confirm_ask("Install playwright?", default="y"):
        return

    if not has_pip:
        success, output = utils.run_install(pip_cmd)
        if not success:
            io.tool_error(output)
            return

    success, output = utils.run_install(chromium_cmd)
    if not success:
        io.tool_error(output)
        return

    return True


class Scraper:
    pandoc_available = None
    playwright_available = None
    playwright_instructions_shown = False

    # Public API...
    def __init__(self, print_error=None, playwright_available=None, verify_ssl=True):
        """
        `print_error` - a function to call to print error/debug info.
        `verify_ssl` - if False, disable SSL certificate verification when scraping.
        """
        if print_error:
            self.print_error = print_error
        else:
            self.print_error = print

        self.playwright_available = playwright_available
        self.verify_ssl = verify_ssl

    def scrape(self, url):
        """
        Scrape a url and turn it into readable markdown if it's HTML.
        If it's plain text or non-HTML, return it as-is.

        `url` - the URL to scrape.
        """

        if self.playwright_available:
            content, mime_type = self.scrape_with_playwright(url)
        else:
            content, mime_type = self.scrape_with_httpx(url)

        if not content:
            self.print_error(f"Failed to retrieve content from {url}")
            return None

        # Check if the content is HTML based on MIME type or content
        if (mime_type and mime_type.startswith("text/html")) or (
            mime_type is None and self.looks_like_html(content)
        ):
            self.try_pandoc()
            content = self.html_to_markdown(content)

        return content

    def looks_like_html(self, content):
        """
        Check if the content looks like HTML.
        """
        if isinstance(content, str):
            # Check for common HTML tags
            html_patterns = [
                r"<!DOCTYPE\s+html",
                r"<html",
                r"<head",
                r"<body",
                r"<div",
                r"<p>",
                r"<a\s+href=",
            ]
            return any(re.search(pattern, content, re.IGNORECASE) for pattern in html_patterns)
        return False

    # Internals...
    def scrape_with_playwright(self, url):
        import playwright  # noqa: F401
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:
                self.playwright_available = False
                self.print_error(str(e))
                return None, None

            try:
                context = browser.new_context(ignore_https_errors=not self.verify_ssl)
                page = context.new_page()

                user_agent = page.evaluate("navigator.userAgent")
                user_agent = user_agent.replace("Headless", "")
                user_agent = user_agent.replace("headless", "")
                user_agent += " " + aider_user_agent

                page.set_extra_http_headers({"User-Agent": user_agent})

                response = None
                try:
                    response = page.goto(url, wait_until="networkidle", timeout=5000)
                except PlaywrightTimeoutError:
                    self.print_error(f"Timeout while loading {url}")
                except PlaywrightError as e:
                    self.print_error(f"Error navigating to {url}: {str(e)}")
                    return None, None

                try:
                    content = page.content()
                    mime_type = None
                    if response:
                        content_type = response.header_value("content-type")
                        if content_type:
                            mime_type = content_type.split(";")[0]
                except PlaywrightError as e:
                    self.print_error(f"Error retrieving page content: {str(e)}")
                    content = None
                    mime_type = None
            finally:
                browser.close()

        return content, mime_type

    def scrape_with_httpx(self, url):
        import httpx

        headers = {"User-Agent": f"Mozilla./5.0 ({aider_user_agent})"}
        try:
            with httpx.Client(headers=headers, verify=self.verify_ssl) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text, response.headers.get("content-type", "").split(";")[0]
        except httpx.HTTPError as http_err:
            self.print_error(f"HTTP error occurred: {http_err}")
        except Exception as err:
            self.print_error(f"An error occurred: {err}")
        return None, None

    def try_pandoc(self):
        if self.pandoc_available:
            return

        try:
            pypandoc.get_pandoc_version()
            self.pandoc_available = True
            return
        except OSError:
            pass

        try:
            pypandoc.download_pandoc(delete_installer=True)
        except Exception as err:
            self.print_error(f"Unable to install pandoc: {err}")
            return

        self.pandoc_available = True

    def html_to_markdown(self, page_source):
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(page_source, "html.parser")
        soup = slimdown_html(soup)
        page_source = str(soup)

        if not self.pandoc_available:
            return page_source

        try:
            md = pypandoc.convert_text(page_source, "markdown", format="html")
        except OSError:
            return page_source

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
