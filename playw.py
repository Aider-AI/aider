import asyncio
from playwright.async_api import async_playwright
import sys

async def main(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        content = await page.content()
        print(content)
        await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playw.py <URL>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
