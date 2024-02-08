import os
import tempfile
from pathlib import Path
from typing import Type

import git
from bs4 import BeautifulSoup
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeDriverService
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.options import ArgOptions as BrowserOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeDriverService
from selenium.webdriver.edge.webdriver import WebDriver as EdgeDriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as GeckoDriverService
from selenium.webdriver.firefox.webdriver import WebDriver as FirefoxDriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.safari.webdriver import WebDriver as SafariDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager as EdgeDriverManager

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}

from aider.dump import dump  # noqa: F401


class IgnorantTemporaryDirectory:
    def __init__(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def __enter__(self):
        return self.temp_dir.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.temp_dir.__exit__(exc_type, exc_val, exc_tb)
        except (OSError, PermissionError):
            pass  # Ignore errors (Windows)


class ChdirTemporaryDirectory(IgnorantTemporaryDirectory):
    def __init__(self):
        try:
            self.cwd = os.getcwd()
        except FileNotFoundError:
            self.cwd = None

        super().__init__()

    def __enter__(self):
        res = super().__enter__()
        os.chdir(self.temp_dir.name)
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cwd:
            try:
                os.chdir(self.cwd)
            except FileNotFoundError:
                pass
        super().__exit__(exc_type, exc_val, exc_tb)


class GitTemporaryDirectory(ChdirTemporaryDirectory):
    def __enter__(self):
        dname = super().__enter__()
        self.repo = make_repo(dname)
        return dname

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.repo
        super().__exit__(exc_type, exc_val, exc_tb)


def make_repo(path=None):
    if not path:
        path = "."
    repo = git.Repo.init(path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "testuser@example.com").release()

    return repo


def is_image_file(file_name):
    """
    Check if the given file name has an image file extension.

    :param file_name: The name of the file to check.
    :return: True if the file is an image, False otherwise.
    """
    file_name = str(file_name)  # Convert file_name to string
    return any(file_name.endswith(ext) for ext in IMAGE_EXTENSIONS)


def safe_abs_path(res):
    "Gives an abs path, which safely returns a full (not 8.3) windows path"
    res = Path(res).resolve()
    return str(res)


def show_messages(messages, title=None, functions=None):
    if title:
        print(title.upper(), "*" * 50)

    for msg in messages:
        role = msg["role"].upper()
        content = msg.get("content")
        if isinstance(content, list):  # Handle list content (e.g., image messages)
            for item in content:
                if isinstance(item, dict) and "image_url" in item:
                    print(role, "Image URL:", item["image_url"]["url"])
        elif isinstance(content, str):  # Handle string content
            for line in content.splitlines():
                print(role, line)
        content = msg.get("function_call")
        if content:
            print(role, content)

    if functions:
        dump(functions)


def is_gpt4_with_openai_base_url(model_name, client):
    """
    Check if the model_name starts with 'gpt-4' and the client base URL includes 'api.openai.com'.

    :param model_name: The name of the model to check.
    :param client: The OpenAI client instance.
    :return: True if conditions are met, False otherwise.
    """
    if client is None or not hasattr(client, "base_url"):
        return False
    return model_name.startswith("gpt-4") and "api.openai.com" in client.base_url.host


# Taken from AutoGPT, MIT License
def open_page_in_browser(
    url: str,
    selenium_web_browser="chrome",
    selenium_headless=True,
    platform="linux",
    user_agent="Aider CLI 0.23.0",
) -> WebDriver:
    """Open a browser window and load a web page using Selenium

    Params:
        url (str): The URL of the page to load
        config (Config): The applicable application configuration

    Returns:
        driver (WebDriver): A driver object representing the browser window to scrape
    """
    options_available: dict[str, Type[BrowserOptions]] = {
        "chrome": ChromeOptions,
        "edge": EdgeOptions,
        "firefox": FirefoxOptions,
        "safari": SafariOptions,
    }

    options: BrowserOptions = options_available[selenium_web_browser]()
    options.add_argument(f"user-agent={user_agent}")

    if selenium_web_browser == "firefox":
        if selenium_headless:
            options.headless = True
            options.add_argument("--disable-gpu")
        driver = FirefoxDriver(
            service=GeckoDriverService(GeckoDriverManager().install()), options=options
        )
    elif selenium_web_browser == "edge":
        driver = EdgeDriver(
            service=EdgeDriverService(EdgeDriverManager().install()), options=options
        )
    elif selenium_web_browser == "safari":
        # Requires a bit more setup on the users end.
        # See https://developer.apple.com/documentation/webkit/testing_with_webdriver_in_safari  # noqa: E501
        driver = SafariDriver(options=options)
    else:
        if platform == "linux" or platform == "linux2":
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--remote-debugging-port=9222")

        options.add_argument("--no-sandbox")
        if selenium_headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")

        chromium_driver_path = Path("/usr/bin/chromedriver")

        driver = ChromeDriver(
            service=(
                ChromeDriverService(str(chromium_driver_path))
                if chromium_driver_path.exists()
                else ChromeDriverService(ChromeDriverManager().install())
            ),
            options=options,
        )
    driver.get(url)

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    return driver


# Taken from AutoGPT, MIT License
def scrape_text_with_selenium(driver: WebDriver) -> str:
    """Scrape text from a browser window using selenium

    Args:
        driver (WebDriver): A driver object representing the browser window to scrape

    Returns:
        str: the text scraped from the website
    """

    # Get the HTML content directly from the browser's DOM
    page_source = driver.execute_script("return document.body.outerHTML;")
    soup = BeautifulSoup(page_source, "html.parser")

    for script in soup(["script", "style"]):
        script.extract()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)
    return text


def scrape(url: str):
    driver = open_page_in_browser(url)
    text = scrape_text_with_selenium(driver)
    driver.quit()
    return text
