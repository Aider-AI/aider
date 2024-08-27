import os
import subprocess
import sys
from io import BytesIO


def run_cmd(command):
    import sys

    if not sys.stdin.isatty():
        return run_cmd_subprocess(command)

    try:
        import pexpect  # noqa: F401
    except ImportError:
        return run_cmd_subprocess(command)

    return run_cmd_pexpect(command)


def run_cmd_subprocess(command):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            encoding=sys.stdout.encoding,
            errors="replace",
        )
        return result.returncode, result.stdout
    except Exception as e:
        return 1, str(e)


def run_cmd_pexpect(command):
    """
    Run a shell command interactively using pexpect, capturing all output.

    :param command: The command to run as a string.
    :return: A tuple containing (exit_status, output)
    """
    import pexpect

    output = BytesIO()

    def output_callback(b):
        output.write(b)
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
