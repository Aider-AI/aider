#!/usr/bin/env python

import sys
from aider import __version__

from playwright.sync_api import sync_playwright

aider_url = 'https://github.com/paul-gauthier/aider'

def scrape_with_playwright(url):
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:
            print(repr(e))
            return

        # user_agent = ??
        page = browser.new_page()
        user_agent = page.evaluate("navigator.userAgent")
        print(f"User Agent: {user_agent}")
        page.goto(url)
        content = page.content()
        browser.close()

    return content

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playw.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
