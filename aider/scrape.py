#!/usr/bin/env python

import sys
from aider import __version__

from playwright.sync_api import sync_playwright

aider_user_agent= f'Aider/{__version__} https://aider.chat'

PLAYWRIGHT_INFO = '''
For better web scraping, install Playwright chromium:

    playwright install --with-deps chromium

See https://aider.chat/docs/install.html#enable-playwright for more info.
'''

class Scraper:
    playwright_available = None

    def __init__(self, print_error=None):
        if print_error:
            self.print_error = print_error
        else:
            self.print_error = print

    def scrape_with_playwright(self, url):
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:
                print(repr(e))
                return

            page = browser.new_page()

            user_agent = page.evaluate("navigator.userAgent")
            user_agent = user_agent.replace('Headless','')
            user_agent = user_agent.replace('headless', '')
            user_agent += ' ' + aider_user_agent

            page = browser.new_page(user_agent=user_agent)
            page.goto(url)
            content = page.content()
            browser.close()

        return content

    def try_playwright(self):
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
                self.playwright_available = True
            except Exception as e:
                self.playwright_available = False
                self.print_error(PLAYWRIGHT_INFO)

    def scrape_with_httpx(self, url):
        pass

    def scrape(self, url):
        if self.playwright_available is None:
            self.try_playwright()

        if self.playwright_available:
            content = self.scrape_with_playwright(url)
        else:
            content = self.scrape_with_httpx(url)

        return content

def main(url):
    scraper = Scraper()
    content = scraper.scrape(url)
    print(content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playw.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
