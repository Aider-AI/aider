from playwright.sync_api import sync_playwright
import sys
from playwright.__main__ import main as playwright_install

def main(url):
    # Check if Chromium is installed, if not, install it
    with sync_playwright() as p:
        p.chromium.launch()

    with sync_playwright() as p:
        browser = p.chromium.launch(user_agent='Aider v0.24.0-dev')
        page = browser.new_page()
        page.goto(url)
        #page.wait_for_load_state('networkidle')
        content = page.content()
        print(content)
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playw.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
