import os
import platform
import subprocess
import sys
from io import BytesIO

import pexpect
import psutil

# Model-provider credentials that child shells (/run, /test, lint, /git) do not need.
# See https://github.com/Aider-AI/aider/issues/5658
PROVIDER_ENV_KEYS = frozenset(
    {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "DEEPSEEK_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "FIREWORKS_API_KEY",
        "COHERE_API_KEY",
        "TOGETHER_API_KEY",
        "MISTRAL_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GITHUB_COPILOT_TOKEN",
    }
)

SENSITIVE_ENV_SUFFIXES = (
    "_API_KEY",
    "_TOKEN",
    "_SECRET",
    "_ACCESS_KEY",
)

# Secret material aider loaded (--api-key, .env, CLI flags). Any env var with a
# matching value is dropped, even if the name is unrelated.
KNOWN_SECRET_VALUES = set()
MIN_SECRET_VALUE_LEN = 8

AWS_CREDENTIAL_KEY_SUFFIXES = (
    "_ACCESS_KEY_ID",
    "_SECRET_ACCESS_KEY",
    "_SESSION_TOKEN",
    "_SECURITY_TOKEN",
)


def _is_registerable_secret_value(value):
    text = str(value or "").strip()
    return bool(text) and len(text) >= MIN_SECRET_VALUE_LEN


def register_known_secrets(*values):
    for value in values:
        if _is_registerable_secret_value(value):
            KNOWN_SECRET_VALUES.add(value)


def refresh_known_secrets_from_process_env(environ=None):
    """Collect secret values from the current process environment."""
    environ = environ or os.environ
    for key, value in environ.items():
        if _is_registerable_secret_value(value) and is_sensitive_env_key(key):
            KNOWN_SECRET_VALUES.add(value)


def _is_aws_credential_key(upper):
    if upper in PROVIDER_ENV_KEYS:
        return True
    return any(upper.endswith(suffix) for suffix in AWS_CREDENTIAL_KEY_SUFFIXES)


def is_sensitive_env_key(name, profile="run"):
    upper = name.upper()
    if profile == "git" and (upper.startswith("GIT_") or upper.startswith("SSH_")):
        return False
    if upper in PROVIDER_ENV_KEYS:
        return True
    if _is_aws_credential_key(upper):
        return True
    return any(upper.endswith(suffix) for suffix in SENSITIVE_ENV_SUFFIXES)


def should_drop_env_var(name, value, profile="run"):
    if value in KNOWN_SECRET_VALUES:
        return True
    return is_sensitive_env_key(name, profile=profile)


def child_process_environ(base=None, extra=None, profile="run"):
    """Copy an environment with provider credentials removed.

    Child commands launched for /run, /test, lint, and /git inherit the process
    environment by default. Scrubbing provider credentials reduces accidental
    leakage into repository-controlled scripts.

    profile="git" keeps GIT_* and SSH_* vars (still drops known secret values).
    """
    source = os.environ if base is None else base
    env = {
        key: value
        for key, value in source.items()
        if not should_drop_env_var(key, value, profile=profile)
    }
    if extra:
        env.update(extra)
    return env


def run_cmd(command, verbose=False, error_print=None, cwd=None):
    try:
        if sys.stdin.isatty() and hasattr(pexpect, "spawn") and platform.system() != "Windows":
            return run_cmd_pexpect(command, verbose, cwd)

        return run_cmd_subprocess(command, verbose, cwd)
    except OSError as e:
        error_message = f"Error occurred while running command '{command}': {str(e)}"
        if error_print is None:
            print(error_message)
        else:
            error_print(error_message)
        return 1, error_message


def get_windows_parent_process_name():
    try:
        current_process = psutil.Process()
        while True:
            parent = current_process.parent()
            if parent is None:
                break
            parent_name = parent.name().lower()
            if parent_name in ["powershell.exe", "cmd.exe"]:
                return parent_name
            current_process = parent
        return None
    except Exception:
        return None


def run_cmd_subprocess(command, verbose=False, cwd=None, encoding=sys.stdout.encoding):
    if verbose:
        print("Using run_cmd_subprocess:", command)

    try:
        shell = os.environ.get("SHELL", "/bin/sh")
        parent_process = None

        # Determine the appropriate shell
        if platform.system() == "Windows":
            parent_process = get_windows_parent_process_name()
            if parent_process == "powershell.exe":
                command = f"powershell -Command {command}"

        if verbose:
            print("Running command:", command)
            print("SHELL:", shell)
            if platform.system() == "Windows":
                print("Parent process:", parent_process)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            encoding=encoding,
            errors="replace",
            bufsize=0,  # Set bufsize to 0 for unbuffered output
            universal_newlines=True,
            cwd=cwd,
            env=child_process_environ(),
        )

        output = []
        while True:
            chunk = process.stdout.read(1)
            if not chunk:
                break
            print(chunk, end="", flush=True)  # Print the chunk in real-time
            output.append(chunk)  # Store the chunk for later use

        process.wait()
        return process.returncode, "".join(output)
    except Exception as e:
        return 1, str(e)


def run_cmd_pexpect(command, verbose=False, cwd=None):
    """
    Run a shell command interactively using pexpect, capturing all output.

    :param command: The command to run as a string.
    :param verbose: If True, print output in real-time.
    :return: A tuple containing (exit_status, output)
    """
    if verbose:
        print("Using run_cmd_pexpect:", command)

    output = BytesIO()

    def output_callback(b):
        output.write(b)
        return b

    try:
        # Use the SHELL environment variable, falling back to /bin/sh if not set
        shell = os.environ.get("SHELL", "/bin/sh")
        child_env = child_process_environ()
        if verbose:
            print("With shell:", shell)

        if os.path.exists(shell):
            # Use the shell from SHELL environment variable
            if verbose:
                print("Running pexpect.spawn with shell:", shell)
            child = pexpect.spawn(
                shell, args=["-i", "-c", command], encoding="utf-8", cwd=cwd, env=child_env
            )
        else:
            # Fall back to spawning the command directly
            if verbose:
                print("Running pexpect.spawn without shell.")
            child = pexpect.spawn(command, encoding="utf-8", cwd=cwd, env=child_env)

        # Transfer control to the user, capturing output
        child.interact(output_filter=output_callback)

        # Wait for the command to finish and get the exit status
        child.close()
        return child.exitstatus, output.getvalue().decode("utf-8", errors="replace")

    except (pexpect.ExceptionPexpect, TypeError, ValueError) as e:
        error_msg = f"Error running command {command}: {e}"
        return 1, error_msg
