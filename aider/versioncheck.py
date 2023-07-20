import requests
import pkg_resources
import aider
import sys
from pathlib import Path

from aider.dump import dump

def check_version(print_cmd):
    response = requests.get('https://pypi.org/pypi/aider-chat/json')
    data = response.json()
    latest_version = data['info']['version']
    current_version = pkg_resources.get_distribution('aider-chat').version

    if pkg_resources.parse_version(latest_version) <= pkg_resources.parse_version(current_version):
        return

    print_cmd(f"Newer version of `aider-chat` available: {latest_version}")
    py = Path(sys.executable).name
    print_cmd(f"To upgrade, run: {py} -m pip install --upgrade aider-chat")

if __name__ == "__main__":
    check_version(print)
