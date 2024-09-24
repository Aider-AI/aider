import os
import sys
import time
from pathlib import Path

import packaging.version

import aider
from aider import utils
from aider.dump import dump  # noqa: F401

VERSION_CHECK_FNAME = Path.home() / ".aider" / "caches" / "versioncheck"


def install_from_main_branch(io):
    """
    Install the latest development version of aider from the main branch of the GitHub repository.
    Exits the application gracefully if the installation fails.
    """
    prompt = "Install the development version of aider from the main branch?"
    pip_install_args = ["--upgrade", "git+https://github.com/paul-gauthier/aider.git"]

    success = utils.check_pip_install_extra(
        io=io, module=None, prompt=prompt, pip_install_args=pip_install_args, self_update=True
    )

    if success:
        io.tool_output("Development version installed. Re-run aider to use the new version.")
        sys.exit()
    else:
        io.tool_error("Failed to install the development version. Exiting.")
        sys.exit(1)


def install_upgrade(io, latest_version=None):
    """
    Install the latest version of aider from PyPI or provide Docker upgrade instructions.
    Exits the application gracefully if the upgrade fails.
    """
    if latest_version:
        new_ver_text = f"Newer aider version v{latest_version} is available."
    else:
        new_ver_text = "Install the latest version of aider?"

    docker_image = os.environ.get("AIDER_DOCKER_IMAGE")
    if docker_image:
        upgrade_instructions = f"""
{new_ver_text} To upgrade, run:

    docker pull {docker_image}
"""
        io.tool_warning(upgrade_instructions)
        return

    # Attempt to upgrade the main application via pip
    success = utils.check_pip_install_extra(
        io,
        module=None,
        prompt=new_ver_text,
        pip_install_args=["--upgrade", "aider-chat"],
        self_update=True,
    )

    if success:
        io.tool_output("Upgrade successful. Re-run aider to use the new version.")
        sys.exit()
    else:
        io.tool_error("Failed to upgrade the main application. Exiting.")
        sys.exit(1)


def check_version(io, just_check=False, verbose=False):
    if not just_check and VERSION_CHECK_FNAME.exists():
        day = 60 * 60 * 24
        since = time.time() - os.path.getmtime(VERSION_CHECK_FNAME)
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
        VERSION_CHECK_FNAME.parent.mkdir(parents=True, exist_ok=True)
        VERSION_CHECK_FNAME.touch()

    ###
    # is_update_available = True

    if just_check or verbose:
        if is_update_available:
            io.tool_output("Update available")
        else:
            io.tool_output("No update available")

    if just_check:
        return is_update_available

    if not is_update_available:
        return False

    install_upgrade(io, latest_version)
    return True
