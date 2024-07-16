import requests

from aider import urls


def test_urls():
    url_attributes = [
        attr
        for attr in dir(urls)
        if not callable(getattr(urls, attr)) and not attr.startswith("__")
    ]
    for attr in url_attributes:
        url = getattr(urls, attr)
        response = requests.get(url)
        assert response.status_code == 200, f"URL {url} returned status code {response.status_code}"
