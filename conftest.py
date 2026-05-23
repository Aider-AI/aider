import pytest  # noqa: F401


def pytest_addoption(parser):
    parser.addoption(
        "--playwright-ws-endpoint",
        metavar="URL",
        default=None,
        help=(
            "Specify the WebSocket endpoint for a Playwright browser server to connect to "
            "(default: None, use the locally installed Playwright)."
        ),
    )
