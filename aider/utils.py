import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import oslex
from rich.console import Console

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
    """
    Minimal spinner that scans a single marker back and forth across a line.

    The animation is pre-rendered into a list of frames.  If the terminal
    cannot display unicode the frames are converted to plain ASCII.
    """

    last_frame_idx = 0  # Class variable to store the last frame index

    def __init__(self, text: str, width: int = 7):
        self.text = text
        self.start_time = time.time()
        self.last_update = 0.0
        self.visible = False
        self.is_tty = sys.stdout.isatty()
        self.console = Console()

        # Pre-render the animation frames using pure ASCII so they will
        # always display, even on very limited terminals.
        ascii_frames = [
            "#=        ",  # C1 C2 space(8)
            "=#        ",  # C2 C1 space(8)
            " =#       ",  # space(1) C2 C1 space(7)
            "  =#      ",  # space(2) C2 C1 space(6)
            "   =#     ",  # space(3) C2 C1 space(5)
            "    =#    ",  # space(4) C2 C1 space(4)
            "     =#   ",  # space(5) C2 C1 space(3)
            "      =#  ",  # space(6) C2 C1 space(2)
            "       =# ",  # space(7) C2 C1 space(1)
            "        =#",  # space(8) C2 C1
            "        #=",  # space(8) C1 C2
            "       #= ",  # space(7) C1 C2 space(1)
            "      #=  ",  # space(6) C1 C2 space(2)
            "     #=   ",  # space(5) C1 C2 space(3)
            "    #=    ",  # space(4) C1 C2 space(4)
            "   #=     ",  # space(3) C1 C2 space(5)
            "  #=      ",  # space(2) C1 C2 space(6)
            " #=       ",  # space(1) C1 C2 space(7)
        ]

        self.unicode_palette = "░█"
        xlate_from, xlate_to = ("=#", self.unicode_palette)

        # If unicode is supported, swap the ASCII chars for nicer glyphs.
        if self._supports_unicode():
            translation_table = str.maketrans(xlate_from, xlate_to)
            frames = [f.translate(translation_table) for f in ascii_frames]
            self.scan_char = xlate_to[xlate_from.find("#")]
        else:
            frames = ascii_frames
            self.scan_char = "#"

        # Bounce the scanner back and forth.
        self.frames = frames
        self.frame_idx = Spinner.last_frame_idx  # Initialize from class variable
        self.width = len(frames[0]) - 2  # number of chars between the brackets
        self.animation_len = len(frames[0])
        self.last_display_len = 0  # Length of the last spinner line (frame + text)

    def _supports_unicode(self) -> bool:
        if not self.is_tty:
            return False
        try:
            out = self.unicode_palette
            out += "\b" * len(self.unicode_palette)
            out += " " * len(self.unicode_palette)
            out += "\b" * len(self.unicode_palette)
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception:
            return False

    def _next_frame(self) -> str:
        frame = self.frames[self.frame_idx]
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        Spinner.last_frame_idx = self.frame_idx  # Update class variable
        return frame

    def step(self, text: str = None) -> None:
        if text is not None:
            self.text = text

        if not self.is_tty:
            return

        now = time.time()
        if not self.visible and now - self.start_time >= 0.5:
            self.visible = True
            self.last_update = 0.0
            if self.is_tty:
                self.console.show_cursor(False)

        if not self.visible or now - self.last_update < 0.1:
            return

        self.last_update = now
        frame_str = self._next_frame()

        # Determine the maximum width for the spinner line
        # Subtract 2 as requested, to leave a margin or prevent cursor wrapping issues
        max_spinner_width = self.console.width - 2
        if max_spinner_width < 0:  # Handle extremely narrow terminals
            max_spinner_width = 0

        current_text_payload = f" {self.text}"
        line_to_display = f"{frame_str}{current_text_payload}"

        # Truncate the line if it's too long for the console width
        if len(line_to_display) > max_spinner_width:
            line_to_display = line_to_display[:max_spinner_width]

        len_line_to_display = len(line_to_display)

        # Calculate padding to clear any remnants from a longer previous line
        padding_to_clear = " " * max(0, self.last_display_len - len_line_to_display)

        # Write the spinner frame, text, and any necessary clearing spaces
        sys.stdout.write(f"\r{line_to_display}{padding_to_clear}")
        self.last_display_len = len_line_to_display

        # Calculate number of backspaces to position cursor at the scanner character
        scan_char_abs_pos = frame_str.find(self.scan_char)

        # Total characters written to the line (frame + text + padding)
        total_chars_written_on_line = len_line_to_display + len(padding_to_clear)

        # num_backspaces will be non-positive if scan_char_abs_pos is beyond
        # total_chars_written_on_line (e.g., if the scan char itself was truncated).
        # (e.g., if the scan char itself was truncated).
        # In such cases, (effectively) 0 backspaces are written,
        # and the cursor stays at the end of the line.
        num_backspaces = total_chars_written_on_line - scan_char_abs_pos
        sys.stdout.write("\b" * num_backspaces)
        sys.stdout.flush()

    def end(self) -> None:
        if self.visible and self.is_tty:
            clear_len = self.last_display_len  # Use the length of the last displayed content
            sys.stdout.write("\r" + " " * clear_len + "\r")
            sys.stdout.flush()
            self.console.show_cursor(True)
        self.visible = False


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
    return oslex.join(cmd_list)


def main():
    spinner = Spinner("Running spinner...")
    try:
        for _ in range(100):
            time.sleep(0.15)
            spinner.step()
        print("Success!")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        spinner.end()


if __name__ == "__main__":
    main()
