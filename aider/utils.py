import itertools
import os
import platform
import shlex
import subprocess
import sys
import itertools
import os
import platform
import shlex
import subprocess
import sys # Ensure sys is imported
import tempfile
import threading # Add threading import
import time # Ensure time is imported
from pathlib import Path

from aider.dump import dump  # noqa: F401

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp", ".pdf"}


class IgnorantTemporaryDirectory:
    def __init__(self):
        if sys.version_info >= (3, 10):
            self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        else:
            self.temp_dir = tempfile.TemporaryDirectory()

    def __enter__(self):
        return self.temp_dir.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        try:
            self.temp_dir.cleanup()
        except (OSError, PermissionError, RecursionError):
            pass  # Ignore errors (Windows and potential recursion)

    def __getattr__(self, item):
        return getattr(self.temp_dir, item)


class ChdirTemporaryDirectory(IgnorantTemporaryDirectory):
    def __init__(self):
        try:
            self.cwd = os.getcwd()
        except FileNotFoundError:
            self.cwd = None

        super().__init__()

    def __enter__(self):
        res = super().__enter__()
        os.chdir(Path(self.temp_dir.name).resolve())
        return res

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cwd:
            try:
                os.chdir(self.cwd)
            except FileNotFoundError:
                pass
        super().__exit__(exc_type, exc_val, exc_tb)


class GitTemporaryDirectory(ChdirTemporaryDirectory):
    def __enter__(self):
        dname = super().__enter__()
        self.repo = make_repo(dname)
        return dname

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.repo
        super().__exit__(exc_type, exc_val, exc_tb)


def make_repo(path=None):
    import git

    if not path:
        path = "."
    repo = git.Repo.init(path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "testuser@example.com").release()

    return repo


def is_image_file(file_name):
    """
    Check if the given file name has an image file extension.

    :param file_name: The name of the file to check.
    :return: True if the file is an image, False otherwise.
    """
    file_name = str(file_name)  # Convert file_name to string
    return any(file_name.endswith(ext) for ext in IMAGE_EXTENSIONS)


def safe_abs_path(res):
    "Gives an abs path, which safely returns a full (not 8.3) windows path"
    res = Path(res).resolve()
    return str(res)


def format_content(role, content):
    formatted_lines = []
    for line in content.splitlines():
        formatted_lines.append(f"{role} {line}")
    return "\n".join(formatted_lines)


def format_messages(messages, title=None):
    output = []
    if title:
        output.append(f"{title.upper()} {'*' * 50}")

    for msg in messages:
        output.append("-------")
        role = msg["role"].upper()
        content = msg.get("content")
        if isinstance(content, list):  # Handle list content (e.g., image messages)
            for item in content:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, dict) and "url" in value:
                            output.append(f"{role} {key.capitalize()} URL: {value['url']}")
                        else:
                            output.append(f"{role} {key}: {value}")
                else:
                    output.append(f"{role} {item}")
        elif isinstance(content, str):  # Handle string content
            output.append(format_content(role, content))
        function_call = msg.get("function_call")
        if function_call:
            output.append(f"{role} Function Call: {function_call}")

    return "\n".join(output)


def show_messages(messages, title=None, functions=None):
    formatted_output = format_messages(messages, title)
    print(formatted_output)

    if functions:
        dump(functions)


def split_chat_history_markdown(text, include_tool=False):
    messages = []
    user = []
    assistant = []
    tool = []
    lines = text.splitlines(keepends=True)

    def append_msg(role, lines):
        lines = "".join(lines)
        if lines.strip():
            messages.append(dict(role=role, content=lines))

    for line in lines:
        if line.startswith("# "):
            continue
        if line.startswith("> "):
            append_msg("assistant", assistant)
            assistant = []
            append_msg("user", user)
            user = []
            tool.append(line[2:])
            continue
        # if line.startswith("#### /"):
        #    continue

        if line.startswith("#### "):
            append_msg("assistant", assistant)
            assistant = []
            append_msg("tool", tool)
            tool = []

            content = line[5:]
            user.append(content)
            continue

        append_msg("user", user)
        user = []
        append_msg("tool", tool)
        tool = []

        assistant.append(line)

    append_msg("assistant", assistant)
    append_msg("user", user)

    if not include_tool:
        messages = [m for m in messages if m["role"] != "tool"]

    return messages


def get_pip_install(args):
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--upgrade-strategy",
        "only-if-needed",
    ]
    cmd += args
    return cmd


def run_install(cmd):
    print()
    print("Installing:", printable_shell_command(cmd))

    try:
        output = []
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding=sys.stdout.encoding,
            errors="replace",
        )
        spinner = Spinner("Installing...")

        while True:
            char = process.stdout.read(1)
            if not char:
                break

            output.append(char)
            spinner.step()

        spinner.end()
        return_code = process.wait()
        output = "".join(output)

        if return_code == 0:
            print("Installation complete.")
            print()
            return True, output

    except subprocess.CalledProcessError as e:
        print(f"\nError running pip install: {e}")

    print("\nInstallation failed.\n")

    return False, output


class Spinner:
    unicode_spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    ascii_spinner = ["|", "/", "-", "\\"]

    def __init__(self, text, console=None, initial_delay=0.5): # Add initial_delay parameter
        self.text = text
        self.console = console # Store console
        self.initial_delay = initial_delay # Store initial_delay
        self.start_time = 0 # Will be set in start()
        self.last_update = 0
        self.visible = False
        self.tested = False
        self.spinner_chars = None # Initialize here
        self._update_is_tty() # Initial check

        # Threading attributes
        self.running = False
        self.thread = None
        self.lock = threading.Lock() # Add a lock for thread-safe printing

    def _update_is_tty(self):
        """Check if output is to a TTY using console if available."""
        if self.console:
            self.is_tty = self.console.is_terminal
        else:
            # Fallback for when console is not provided
            try:
                self.is_tty = sys.stdout.isatty()
            except Exception: # Catch potential errors like detached stdout
                self.is_tty = False

    def test_charset(self):
        if self.tested:
            return
        self.tested = True
        # Try unicode first, fall back to ascii if needed
        try:
            # Test if we can print unicode characters
            print(self.unicode_spinner[0], end="", flush=True)
            print("\r", end="", flush=True)
            self.spinner_chars = itertools.cycle(self.unicode_spinner)
        except UnicodeEncodeError:
            self.spinner_chars = itertools.cycle(self.ascii_spinner)

    def step(self):
        self._update_is_tty() # Re-check TTY status in case it changes (less likely but safe)
        if not self.is_tty:
            return

        current_time = time.time()
        # Use self.initial_delay for the visibility check
        if not self.visible and current_time - self.start_time >= self.initial_delay:
            self.visible = True
            # Call _print_frame directly the first time it becomes visible
            self._print_frame() # Corrected call
            self.last_update = current_time # Set last_update after first print
        elif self.visible and current_time - self.last_update >= 0.1:
             # Subsequent updates based on interval
            self._print_frame()
            self.last_update = current_time

    def _print_frame(self):
        # Actual printing logic, separated for clarity
        if not self.visible: # Should not happen if called from step correctly, but safe check
            return

        if not self.spinner_chars: # Ensure charset is tested before first print
             self.test_charset()
             if not self.spinner_chars: # If test_charset failed somehow
                 return

        # Use a lock to prevent race conditions with other prints
        with self.lock:
            # \x1b[2K clears the entire line, \r moves cursor to beginning
            clear_line = "\x1b[2K\r"
            # Print clear sequence, text, space, spinner char, space
            # Ensure flush=True
            print(f"{clear_line}{self.text} {next(self.spinner_chars)} ", end="", flush=True)


    def _run(self):
        # The target function for the background thread
        while self.running:
            self.step()
            # Sleep for a short duration to control animation speed and reduce CPU usage
            time.sleep(0.1)

    def start(self):
        # Start the spinner animation in a background thread
        self._update_is_tty()
        if not self.is_tty:
            return # Don't start if not a TTY

        # Test charset before starting the thread to avoid race conditions on first print
        self.test_charset()

        self.start_time = time.time() # Set start time here
        self.running = True
        # Ensure the thread is a daemon so it doesn't block program exit
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        # Stop the spinner animation thread and clear the line
        if not self.thread or not self.running:
            return

        self.running = False
        thread_was_alive = False
        if self.thread and self.thread.is_alive():
            thread_was_alive = True
            # Wait longer (e.g., 1 second) for the thread to finish its cycle and stop
            self.thread.join(timeout=1.0)

        # Only call end if the spinner was actually running/visible to clear the line
        if thread_was_alive or self.visible:
             self.end()

    def end(self):
        # Clears the spinner line if it was visible
        # Clears the spinner line if it was visible
        # This is now separate from stopping the thread
        self._update_is_tty() # Ensure TTY status is current before clearing
        if self.visible and self.is_tty:
            with self.lock: # Use lock for final clear
                # \x1b[2K clears the entire line, \r moves cursor to beginning
                clear_line = "\x1b[2K\r"
                print(clear_line, end="", flush=True)
                self.visible = False # Mark as not visible after clearing


# Keep run_install using manual steps for now, as it's tied to subprocess output
def run_install(cmd):
    print()
    print("Installing:", printable_shell_command(cmd))

    try:
        output = []
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding=sys.stdout.encoding,
            errors="replace",
        )
        spinner = Spinner("Installing...") # Uses default delay

        while True:
            char = process.stdout.read(1)
            if not char:
                break

            output.append(char)
            spinner.step() # Manual step call

        spinner.end() # Manual end call
        return_code = process.wait()
        output = "".join(output)

        if return_code == 0:
            print("Installation complete.")
            print()
            return True, output

    except subprocess.CalledProcessError as e:
        print(f"\nError running pip install: {e}")

    print("\nInstallation failed.\n")

    return False, output


def find_common_root(abs_fnames):
    try:
        if len(abs_fnames) == 1:
            return safe_abs_path(os.path.dirname(list(abs_fnames)[0]))
        elif abs_fnames:
            return safe_abs_path(os.path.commonpath(list(abs_fnames)))
    except OSError:
        pass

    try:
        return safe_abs_path(os.getcwd())
    except FileNotFoundError:
        # Fallback if cwd is deleted
        return "."


def format_tokens(count):
    if count < 1000:
        return f"{count}"
    elif count < 10000:
        return f"{count / 1000:.1f}k"
    else:
        return f"{round(count / 1000)}k"


def touch_file(fname):
    fname = Path(fname)
    try:
        fname.parent.mkdir(parents=True, exist_ok=True)
        fname.touch()
        return True
    except OSError:
        return False


def check_pip_install_extra(io, module, prompt, pip_install_cmd, self_update=False):
    if module:
        try:
            __import__(module)
            return True
        except (ImportError, ModuleNotFoundError, RuntimeError):
            pass

    cmd = get_pip_install(pip_install_cmd)

    if prompt:
        io.tool_warning(prompt)

    if self_update and platform.system() == "Windows":
        io.tool_output("Run this command to update:")
        print()
        print(printable_shell_command(cmd))  # plain print so it doesn't line-wrap
        return

    if not io.confirm_ask("Run pip install?", default="y", subject=printable_shell_command(cmd)):
        return

    success, output = run_install(cmd)
    if success:
        if not module:
            return True
        try:
            __import__(module)
            return True
        except (ImportError, ModuleNotFoundError, RuntimeError) as err:
            io.tool_error(str(err))
            pass

    io.tool_error(output)

    print()
    print("Install failed, try running this command manually:")
    print(printable_shell_command(cmd))


def printable_shell_command(cmd_list):
    """
    Convert a list of command arguments to a properly shell-escaped string.

    Args:
        cmd_list (list): List of command arguments.

    Returns:
        str: Shell-escaped command string.
    """
    if platform.system() == "Windows":
        return subprocess.list2cmdline(cmd_list)
    else:
        return shlex.join(cmd_list)


def main():
    spinner = Spinner("Running spinner...")
    for _ in range(40):  # 40 steps * 0.25 seconds = 10 seconds
        time.sleep(0.25)
        spinner.step()
    spinner.end()


if __name__ == "__main__":
    main()
