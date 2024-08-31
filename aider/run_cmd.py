import os
import platform
import subprocess
import sys
from io import BytesIO

import pexpect


def run_cmd(command, verbose=False):
    import sys

    if sys.stdin.isatty() and hasattr(pexpect, "spawn") and platform.system() != "Windows":
        return run_cmd_pexpect(command, verbose)

    return run_cmd_subprocess(command, verbose)


def run_cmd_subprocess(command, verbose=False):
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            encoding=sys.stdout.encoding,
            errors="replace",
            bufsize=1,
            universal_newlines=True,
        )

        output = []
        for line in process.stdout:
            if verbose:
                print(line, end="")  # Print the line in real-time only if verbose is True
            output.append(line)  # Store the line for later use

        process.wait()
        return process.returncode, "".join(output)
    except Exception as e:
        return 1, str(e)


def run_cmd_pexpect(command, verbose=False):
    """
    Run a shell command interactively using pexpect, capturing all output.

    :param command: The command to run as a string.
    :param verbose: If True, print output in real-time.
    :return: A tuple containing (exit_status, output)
    """
    import pexpect

    output = BytesIO()

    def output_callback(b):
        output.write(b)
        if verbose:
            print(b.decode("utf-8", errors="replace"), end="", flush=True)
        return b

    try:
        # Use the SHELL environment variable, falling back to /bin/sh if not set
        shell = os.environ.get("SHELL", "/bin/sh")

        if os.path.exists(shell):
            # Use the shell from SHELL environment variable
            child = pexpect.spawn(shell, args=["-c", command], encoding="utf-8")
        else:
            # Fall back to spawning the command directly
            child = pexpect.spawn(command, encoding="utf-8")

        # Transfer control to the user, capturing output
        child.interact(output_filter=output_callback)

        # Wait for the command to finish and get the exit status
        child.close()
        return child.exitstatus, output.getvalue().decode("utf-8", errors="replace")

    except pexpect.ExceptionPexpect as e:
        error_msg = f"Error running command: {e}"
        return 1, error_msg
