from playwright.sync_api import sync_playwright
import sys

def main(url):
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
