from playwright.sync_api import sync_playwright
import sys
from playwright.__main__ import main as playwright_install

def main(url):
    # Check if Chromium is installed, if not, install it
    try:
        with sync_playwright() as p:
            p.chromium.launch()
    except Exception as e:
        print("Chromium is not installed. Installing necessary dependencies...")
        playwright_install(['install', 'chromium'])

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        content = page.content()
        print(content)
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playw.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
