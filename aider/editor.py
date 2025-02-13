"""
Editor module for handling system text editor interactions.

This module provides functionality to:
- Discover and launch the system's configured text editor
- Create and manage temporary files for editing
- Handle editor preferences from environment variables
- Support cross-platform editor operations
"""

import os
import platform
import shlex
import subprocess
import tempfile

from rich.console import Console

DEFAULT_EDITOR_NIX = "vi"
DEFAULT_EDITOR_OS_X = "vim"
DEFAULT_EDITOR_WINDOWS = "notepad"

console = Console()


def print_status_message(success, message, style=None):
    """
    Print a status message with appropriate styling.

    :param success: Whether the operation was successful
    :param message: The message to display
    :param style: Optional style override. If None, uses green for success and red for failure
    """
    if style is None:
        style = "bold green" if success else "bold red"
    console.print(message, style=style)
    print("")


def write_temp_file(
    input_data="",
    suffix=None,
    prefix=None,
    dir=None,
):
    """
    Create a temporary file with the given input data.

    :param input_data: Content to write to the temporary file
    :param suffix: Optional file extension (without the dot)
    :param prefix: Optional prefix for the temporary filename
    :param dir: Optional directory to create the file in
    :return: Path to the created temporary file
    :raises: OSError if file creation or writing fails
    """
    kwargs = {"prefix": prefix, "dir": dir}
    if suffix:
        kwargs["suffix"] = f".{suffix}"
    fd, filepath = tempfile.mkstemp(**kwargs)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(input_data)
    except Exception:
        os.close(fd)
        raise
    return filepath


def get_environment_editor(default=None):
    """
    Fetches the preferred editor from the environment variables.

    This function checks the following environment variables in order to
    determine the user's preferred editor:

     - VISUAL
     - EDITOR

    :param default: The default editor to return if no environment variable is set.
    :type default: str or None
    :return: The preferred editor as specified by environment variables or the default value.
    :rtype: str or None
    """
    editor = os.environ.get("VISUAL", os.environ.get("EDITOR", default))
    return editor


def discover_editor(editor_override=None):
    """
    Discovers and returns the editor command parts and environment variables.
    
    Handles environment variables preceding the editor command (e.g. 'VAR=value editor').
    Returns tuple of (command_parts, env_vars_dict)
    """
    system = platform.system()
    if system == "Windows":
        default_editor = DEFAULT_EDITOR_WINDOWS
    elif system == "Darwin":
        default_editor = DEFAULT_EDITOR_OS_X
    else:
        default_editor = DEFAULT_EDITOR_NIX
    if editor_override:
        editor = editor_override
    else:
        editor = get_environment_editor(default_editor)

    try:
        parts = shlex.split(editor)
    except ValueError as e:
        raise RuntimeError(f"Invalid editor command format '{editor}': {e}")

    # Extract environment variables from the beginning of the command
    env_vars = {}
    while parts and '=' in parts[0]:
        key, value = parts.pop(0).split('=', 1)
        env_vars[key] = value

    if not parts:
        raise RuntimeError(f"Editor command missing after environment variables in '{editor}'")

    return parts, env_vars


def pipe_editor(input_data="", suffix=None, editor=None):
    """
    Opens the system editor with optional input data and returns the edited content.

    This function creates a temporary file with the provided input data, opens it in
    the system editor, waits for the user to make changes and close the editor, then
    reads and returns the modified content. The temporary file is deleted afterwards.

    :param input_data: Initial content to populate the editor with
    :type input_data: str
    :param suffix: Optional file extension for the temporary file (e.g. '.txt', '.md')
    :type suffix: str or None
    :return: The edited content after the editor is closed
    :rtype: str
    """
    filepath = write_temp_file(input_data, suffix)
    command_parts, env_vars = discover_editor(editor)
    command_parts.append(filepath)
    
    # Merge our environment variables with the current process environment
    full_env = {**os.environ, **env_vars}
    
    subprocess.call(command_parts, env=full_env)
    with open(filepath, "r") as f:
        output_data = f.read()
    try:
        os.remove(filepath)
    except PermissionError:
        print_status_message(
            False,
            (
                f"WARNING: Unable to delete temporary file {filepath!r}. You may need to delete it"
                " manually."
            ),
        )
    return output_data
