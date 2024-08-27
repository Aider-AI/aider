import os
import sys
import time
from pathlib import Path

import packaging.version

import aider
from aider import utils
from aider.dump import dump  # noqa: F401


def install_from_main_branch(io):
    """
    Install the latest version of aider from the main branch of the GitHub repository.
    """
    return utils.check_pip_install_extra(
        io,
        None,
        "Install the development version of aider from the main branch?",
        ["--upgrade", "git+https://github.com/paul-gauthier/aider.git"],
    )


def install_upgrade(io):
    """
    Install the latest version of aider from PyPI.
    """
    return utils.check_pip_install_extra(
        io,
        None,
        "Install the latest version of aider from PyPI?",
        ["--upgrade", "aider-chat"],
    )


def check_version(io, just_check=False, verbose=False):
    fname = Path.home() / ".aider" / "caches" / "versioncheck"
    if not just_check and fname.exists():
        day = 60 * 60 * 24
        since = time.time() - os.path.getmtime(fname)
        if 0 < since < day:
            if verbose:
                hours = since / 60 / 60
                io.tool_output(f"Too soon to check version: {hours:.1f} hours")
            return

    # To keep startup fast, avoid importing this unless needed
    import requests

    try:
        response = requests.get("https://pypi.org/pypi/aider-chat/json")
        data = response.json()
        latest_version = data["info"]["version"]
        current_version = aider.__version__

        if just_check or verbose:
            io.tool_output(f"Current version: {current_version}")
            io.tool_output(f"Latest version: {latest_version}")

        is_update_available = packaging.version.parse(latest_version) > packaging.version.parse(
            current_version
        )
    except Exception as err:
        io.tool_error(f"Error checking pypi for new version: {err}")
        return False
    finally:
        fname.parent.mkdir(parents=True, exist_ok=True)
        fname.touch()

    if just_check or verbose:
        if is_update_available:
            io.tool_output("Update available")
        else:
            io.tool_output("No update available")

    if just_check:
        return is_update_available

    if not is_update_available:
        return False

    docker_image = os.environ.get("AIDER_DOCKER_IMAGE")
    if docker_image:
        text = f"""
Newer aider version v{latest_version} is available. To upgrade, run:

    docker pull {docker_image}
"""
        io.tool_error(text)
        return True

    cmd = utils.get_pip_install(["--upgrade", "aider-chat"])

    text = f"Newer aider version v{latest_version} is available. To upgrade, run:"

    io.tool_error(text)
    if io.confirm_ask("Run pip install?", subject=" ".join(cmd)):
        success, output = utils.run_install(cmd)
        if success:
            io.tool_output("Re-run aider to use new version.")
            sys.exit()
        else:
            io.tool_error(output)

    return True
