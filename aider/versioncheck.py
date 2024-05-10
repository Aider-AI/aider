import sys

import packaging.version
import requests

import aider


def check_version(print_cmd):
    try:
        response = requests.get("https://pypi.org/pypi/aider-chat/json")
        data = response.json()
        latest_version = data["info"]["version"]
        current_version = aider.__version__

        is_update_available = packaging.version.parse(latest_version) > packaging.version.parse(
            current_version
        )

        if is_update_available:
            print_cmd(
                f"Newer version v{latest_version} is available. To upgrade, run:"  # noqa: E231
            )
            py = sys.executable
            if "pipx" in py:
                print_cmd("pipx upgrade aider-chat")
            else:
                print_cmd(f"{py} -m pip install --upgrade aider-chat")

        return is_update_available
    except Exception as err:
        print_cmd(f"Error checking pypi for new version: {err}")
        return False


if __name__ == "__main__":
    check_version(print)
