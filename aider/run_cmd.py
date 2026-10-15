import os
import platform
import subprocess
import sys
from io import BytesIO

import pexpect
import psutil

# Environment variable names that contain provider credentials and should NOT be
# passed to child processes spawned via /run, /test, lint, or /git commands.
PROVIDER_CREDENTIAL_KEYS = frozenset(
    [
        # OpenAI
        "OPENAI_API_KEY",
        "OPENAI_API_KEY_OLD",
        "OPENAI_ORGANIZATION",
        # Anthropic
        "ANTHROPIC_API_KEY",
        # OpenRouter
        "OPENROUTER_API_KEY",
        # Google
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        # DeepSeek
        "DEEPSEEK_API_KEY",
        # Groq
        "GROQ_API_KEY",
        # Fireworks AI
        "FIREWORKS_API_KEY",
        # Cohere
        "COHERE_API_KEY",
        # AWS (specific keys; suffix patterns handled separately)
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_SECURITY_TOKEN",
        # Azure
        "AZURE_OPENAI_API_KEY",
        "AZURE_API_KEY",
        # Mistral
        "MISTRAL_API_KEY",
        # Together AI
        "TOGETHER_API_KEY",
        # Perplexity
        "PERPLEXITY_API_KEY",
        # Cloudflare
        "CLOUDFLARE_API_KEY",
        # Replicate
        "REPLICATE_API_KEY",
        # Hugging Face
        "HF_TOKEN",
        "HUGGINGFACE_TOKEN",
        # AI21
        "AI21_API_KEY",
        # Aleph Alpha
        "ALEPHALPHA_API_KEY",
        # Scale
        "SCALE_API_KEY",
    ]
)

# Suffixes that identify model-provider credentials. Generic *_TOKEN and
# *_SECRET names are intentionally omitted: child commands such as git and
# user tests need those (GITHUB_TOKEN, GH_TOKEN, and similar).
PROVIDER_CREDENTIAL_SUFFIXES = (
    "_API_KEY",
    "_API_KEY_OLD",
    "_AUTH_TOKEN",
)


def child_process_environ():
    """Return a copy of the current process environment with provider credentials removed.

    Child processes spawned via /run, /test, lint, or /git commands do not need
    access to model-provider credentials. Removing them reduces the attack surface
    if a child process is compromised or runs untrusted code.

    Returns:
        dict: Environment variables with provider credentials scrubbed.
    """
    env = dict(os.environ)

    # Remove keys that are provider credentials
    for key in PROVIDER_CREDENTIAL_KEYS:
        env.pop(key, None)

    # Also remove any key that ends with a known credential suffix, including
    # AWS_*_API_KEY names that are not in the explicit list above.
    keys_to_remove = [
        key for key in env
        if any(key.endswith(suffix) for suffix in PROVIDER_CREDENTIAL_SUFFIXES)
    ]
    for key in keys_to_remove:
        env.pop(key, None)

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
        if verbose:
            print("With shell:", shell)

        if os.path.exists(shell):
            # Use the shell from SHELL environment variable
            if verbose:
                print("Running pexpect.spawn with shell:", shell)
            child = pexpect.spawn(
                shell,
                args=["-i", "-c", command],
                encoding="utf-8",
                cwd=cwd,
                env=child_process_environ(),
            )
        else:
            # Fall back to spawning the command directly
            if verbose:
                print("Running pexpect.spawn without shell.")
            child = pexpect.spawn(
                command,
                encoding="utf-8",
                cwd=cwd,
                env=child_process_environ(),
            )

        # Transfer control to the user, capturing output
        child.interact(output_filter=output_callback)

        # Wait for the command to finish and get the exit status
        child.close()
        return child.exitstatus, output.getvalue().decode("utf-8", errors="replace")

    except (pexpect.ExceptionPexpect, TypeError, ValueError) as e:
        error_msg = f"Error running command {command}: {e}"
        return 1, error_msg
