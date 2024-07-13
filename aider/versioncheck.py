import sys
import time
from pathlib import Path

import packaging.version

import aider
from aider import utils


def check_version(io, just_check=False):
    fname = Path.home() / ".aider" / "caches" / "versioncheck"
    day = 60 * 60 * 24
    if fname.exists() and time.time() - fname.stat().st_mtime < day:
        return

    # To keep startup fast, avoid importing this unless needed
    import requests

    try:
        response = requests.get("https://pypi.org/pypi/aider-chat/json")
        data = response.json()
        latest_version = data["info"]["version"]
        current_version = aider.__version__

        is_update_available = packaging.version.parse(latest_version) > packaging.version.parse(
            current_version
        )
    except Exception as err:
        io.tool_error(f"Error checking pypi for new version: {err}")
        return False
    finally:
        fname.parent.mkdir(parents=True, exist_ok=True)
        fname.touch()

    if just_check:
        return is_update_available

    if not is_update_available:
        return False

    cmd = utils.get_pip_install(["--upgrade", "aider-chat"])

    text = f"""
Newer aider version v{latest_version} is available. To upgrade, run:

    {' '.join(cmd)}
"""
    io.tool_error(text)

    if io.confirm_ask("Run pip install?"):
        if utils.run_install(cmd):
            io.tool_output("Re-run aider to use new version.")
            sys.exit()

    return True
