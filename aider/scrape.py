#!/usr/bin/env python

import ipaddress
import re
import socket
import sys
from urllib.parse import urljoin, urlsplit

import pypandoc

from aider import __version__, urls, utils
from aider.dump import dump  # noqa: F401

aider_user_agent = f"Aider/{__version__} +{urls.website}"

blocked_scrape_hostnames = {
    "metadata.google.internal",
}


class ScrapeNetworkBackend:
    def __init__(self, scraper):
        self.scraper = scraper

    def connect_tcp(
        self,
        host,
        port,
        timeout=None,
        local_address=None,
        socket_options=None,
    ):
        from httpcore import ConnectError, ConnectTimeout
        from httpcore._backends.sync import SyncStream

        addresses, error = self.scraper.get_safe_addresses(
            host, port, "http", f"{host}:{port}"
        )
        if error:
            raise ConnectError(error)

        last_error = None
        for family, socktype, proto, sockaddr, _ip in addresses:
            sock = None
            try:
                sock = socket.socket(family, socktype, proto)
                sock.settimeout(timeout)
                if local_address is not None:
                    if family == socket.AF_INET6:
                        sock.bind((local_address, 0, 0, 0))
                    else:
                        sock.bind((local_address, 0))
                if socket_options:
                    for option in socket_options:
                        sock.setsockopt(*option)
                sock.connect(sockaddr)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                return SyncStream(sock)
            except socket.timeout as err:
                last_error = err
            except OSError as err:
                last_error = err

            if sock is not None:
                sock.close()

        if isinstance(last_error, socket.timeout):
            raise ConnectTimeout(str(last_error))
        raise ConnectError(str(last_error or f"Unable to connect to {host}:{port}"))

    def connect_unix_socket(self, path, timeout=None, socket_options=None):
        from httpcore._backends.sync import SyncBackend

        return SyncBackend().connect_unix_socket(path, timeout, socket_options)

    def sleep(self, seconds):
        from time import sleep

        sleep(seconds)


# Playwright is nice because it has a simple way to install dependencies on most
# platforms.


def check_env():
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

    return has_pip, has_chromium


def has_playwright():
    has_pip, has_chromium = check_env()
    return has_pip and has_chromium


def install_playwright(io):
    has_pip, has_chromium = check_env()
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
        self._blocked_playwright_request_error = None

    def scrape(self, url):
        """
        Scrape a url and turn it into readable markdown if it's HTML.
        If it's plain text or non-HTML, return it as-is.

        `url` - the URL to scrape.
        """

        error = self.validate_url(url)
        if error:
            self.print_error(error)
            return None

        if self.playwright_available and self.can_use_playwright_for_url(url):
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

    def validate_url(self, url):
        """
        Return an error if the URL targets a private or otherwise non-public network.
        """
        try:
            parsed_url = urlsplit(url)
        except ValueError as err:
            return f"Invalid URL {url}: {err}"

        if parsed_url.scheme not in ("http", "https"):
            return None

        hostname = parsed_url.hostname
        if not hostname:
            return f"Invalid URL {url}: missing hostname"

        if hostname.lower().rstrip(".") in blocked_scrape_hostnames:
            return f"Blocked scraping private or metadata URL: {url}"

        try:
            port = parsed_url.port
        except ValueError as err:
            return f"Invalid URL {url}: {err}"

        _addresses, error = self.get_safe_addresses(hostname, port, parsed_url.scheme, url)
        if error:
            return error

    def get_safe_addresses(self, hostname, port, scheme, display_url):
        if hostname.lower().rstrip(".") in blocked_scrape_hostnames:
            return [], f"Blocked scraping private or metadata URL: {display_url}"

        addresses, error = self.resolve_url_addresses(hostname, port, scheme)
        if error:
            return [], error

        if not addresses:
            return [], f"Unable to resolve URL host {hostname}: no addresses found"

        for _family, _socktype, _proto, _sockaddr, ip in addresses:
            if not self.is_public_unicast_address(ip):
                return [], f"Blocked scraping private or metadata URL: {display_url}"

        return addresses, None

    def is_public_unicast_address(self, ip):
        return (
            ip.is_global
            and not ip.is_multicast
            and not ip.is_reserved
            and not ip.is_unspecified
        )

    def resolve_url_addresses(self, hostname, port, scheme):
        if port is None:
            port = 443 if scheme == "https" else 80

        try:
            infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except OSError as err:
            return [], f"Unable to resolve URL host {hostname}: {err}"

        addresses = []
        for info in infos:
            address = info[4][0]
            try:
                ip = ipaddress.ip_address(address)
            except ValueError:
                continue
            addresses.append((info[0], info[1], info[2], info[4], ip))

        return addresses, None

    def can_use_playwright_for_url(self, url):
        try:
            parsed_url = urlsplit(url)
        except ValueError:
            return False

        if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
            return False

        try:
            ipaddress.ip_address(parsed_url.hostname)
        except ValueError:
            return False
        return True

    def validate_playwright_url(self, url):
        error = self.validate_url(url)
        if error:
            return error

        try:
            parsed_url = urlsplit(url)
        except ValueError as err:
            return f"Invalid URL {url}: {err}"

        if parsed_url.scheme in ("http", "https"):
            try:
                ipaddress.ip_address(parsed_url.hostname)
            except ValueError:
                return f"Blocked scraping browser URL that requires DNS resolution: {url}"

    def route_scrape_request(self, route):
        error = self.validate_playwright_url(route.request.url)
        if error:
            if not self._blocked_playwright_request_error:
                self._blocked_playwright_request_error = error
            route.abort()
            return

        route.continue_()

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
                self._blocked_playwright_request_error = None
                page.route("**/*", self.route_scrape_request)

                user_agent = page.evaluate("navigator.userAgent")
                user_agent = user_agent.replace("Headless", "")
                user_agent = user_agent.replace("headless", "")
                user_agent += " " + aider_user_agent

                page.set_extra_http_headers({"User-Agent": user_agent})

                response = None
                try:
                    response = page.goto(url, wait_until="networkidle", timeout=5000)
                except PlaywrightTimeoutError:
                    print(f"Page didn't quiesce, scraping content anyway: {url}")
                    response = None
                except PlaywrightError as e:
                    if self._blocked_playwright_request_error:
                        self.print_error(self._blocked_playwright_request_error)
                    else:
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
            transport = httpx.HTTPTransport(verify=self.verify_ssl, trust_env=False)
            transport._pool._network_backend = ScrapeNetworkBackend(self)
            with httpx.Client(
                headers=headers,
                follow_redirects=False,
                transport=transport,
                trust_env=False,
            ) as client:
                for _ in range(20):
                    error = self.validate_url(url)
                    if error:
                        self.print_error(error)
                        return None, None

                    response = client.get(url)
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            response.raise_for_status()
                        url = urljoin(str(response.url), location)
                        continue

                    response.raise_for_status()
                    return response.text, response.headers.get("content-type", "").split(";")[0]

                self.print_error(f"Too many redirects while scraping {url}")
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
    scraper = Scraper(playwright_available=has_playwright())
    content = scraper.scrape(url)
    print(content)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python playw.py <URL>")
        sys.exit(1)
    main(sys.argv[1])
