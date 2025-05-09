import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from pathlib import Path

import oslex
from rich.console import Console
from rich.text import Text

from aider.dump import dump  # noqa: F401

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp", ".pdf"}


class SpinnerStyle(Enum):
    DEFAULT = "default"
    KITT = "kitt"


@dataclass
class SpinnerConfig:
    style: SpinnerStyle = SpinnerStyle.DEFAULT
    color: str = "default"  # Color for spinner text, actual application may vary
    width: int = 7  # Width for KITT spinner, default spinner has fixed frame width


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
        spinner = Spinner("Installing...", config=SpinnerConfig())

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
    Minimal spinner.
    Supports a KITT-like scanner animation if Unicode is supported and style is KITT.
    Otherwise, falls back to a simpler ASCII/default Unicode animation.
    """

    KITT_CHARS = ["\u2591", "\u2592", "\u2593", "\u2588"]  # ░, ▒, ▓, █
    ASCII_FRAMES = [
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
    # For testing unicode support robustly, includes a KITT char and an old palette char
    UNICODE_TEST_CHARS = KITT_CHARS[3] + "≋"

    last_frame_idx = 0  # Class variable for ASCII spinner starting frame

    def __init__(self, text: str, config: SpinnerConfig):
        self.text = text
        self.config = config
        self.start_time = time.time()
        self.last_update = 0.0
        self.visible = False
        self.is_tty = sys.stdout.isatty()
        self.console = Console()
        self.last_display_len = 0

        self.use_kitt_animation = False
        self.default_spinner_frames = None
        self.default_spinner_scan_char = None
        self.default_spinner_content_width = 0

        if self.config.style == SpinnerStyle.KITT and self._supports_unicode_for_kitt():
            self.use_kitt_animation = True
            self.SCANNER_WIDTH = max(self.config.width, 4)
            self.scanner_position = 0
            self.scanner_direction = 1
            self.animation_len = self.SCANNER_WIDTH
            # For KITT, the "scan char" for cursor positioning is the head of the scanner.
            # Its actual character changes, so logic in step() will be different.
            # We use KITT_CHARS[3] as a representative for finding its position.
            self.scan_char_for_cursor_logic = self.KITT_CHARS[3]
        else:
            if self.config.style == SpinnerStyle.KITT: # and KITT unicode failed
                # This warning ideally should use self.io, but Spinner doesn't have it.
                # A simple print is a fallback.
                # Consider passing io or a logger if this needs to be more robust.
                if self.is_tty:
                    print("\rWarning: KITT spinner requires better unicode support, falling back to default spinner.", file=sys.stderr)

            # Setup for DEFAULT style (original spinner logic) or KITT fallback
            self.default_spinner_frames = list(self.ASCII_FRAMES) # Start with ASCII
            self.default_spinner_scan_char = "#"
            self.original_unicode_palette = "░█"

            if self._supports_unicode_for_default_style():
                translation_table = str.maketrans("=#", self.original_unicode_palette)
                self.default_spinner_frames = [f.translate(translation_table) for f in self.ASCII_FRAMES]
                try:
                    # '#' is the first char of '=#', find its translated counterpart
                    # The original logic was: xlate_to[xlate_from.find("#")]
                    # xlate_from = "=#", xlate_to = self.original_unicode_palette
                    # So, if '#' is at index 0 of "=#", use index 0 of palette.
                    # If '=' is at index 0 of "=#", use index 0 of palette.
                    # This seems to imply self.scan_char should be based on what '#' translates to.
                    # Assuming '#' is the primary moving part of the ASCII spinner.
                    self.default_spinner_scan_char = self.original_unicode_palette[self.ASCII_FRAMES[0].find("#")]
                except IndexError:
                    self.default_spinner_scan_char = self.original_unicode_palette[0] if self.original_unicode_palette else "#"


            self.frame_idx = Spinner.last_frame_idx
            self.default_spinner_content_width = len(self.default_spinner_frames[0]) - 2
            self.animation_len = len(self.default_spinner_frames[0])


    def _supports_unicode_for_kitt(self) -> bool:
        if not self.is_tty:
            return False
        try:
            # Test with a KITT character and one from the old palette for broader check
            chars_to_test = self.UNICODE_TEST_CHARS
            num_chars_printed = len(chars_to_test)

            out = chars_to_test
            out += "\b" * num_chars_printed
            out += " " * num_chars_printed
            out += "\b" * num_chars_printed
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception: # Broad exception to catch any other terminal issues
            return False

    def _supports_unicode_for_default_style(self) -> bool:
        if not self.is_tty:
            return False
        try:
            out = self.original_unicode_palette
            out += "\b" * len(self.original_unicode_palette)
            out += " " * len(self.original_unicode_palette)
            out += "\b" * len(self.original_unicode_palette)
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception:
            return False

    def _next_frame(self) -> str:
        if self.use_kitt_animation:
            # KITT scanner animation logic (from patch)
            current_display_chars = [" "] * self.SCANNER_WIDTH

            if 0 <= self.scanner_position < self.SCANNER_WIDTH:
                current_display_chars[self.scanner_position] = self.KITT_CHARS[3]

            tail_symbols = [self.KITT_CHARS[2], self.KITT_CHARS[1], self.KITT_CHARS[0]]
            for i, tail_symbol in enumerate(tail_symbols):
                distance_from_head = i + 1
                tail_pos = self.scanner_position - distance_from_head if self.scanner_direction == 1 else self.scanner_position + distance_from_head
                if 0 <= tail_pos < self.SCANNER_WIDTH:
                    current_display_chars[tail_pos] = tail_symbol
            
            if self.SCANNER_WIDTH <= 0: return "".join(current_display_chars)

            if self.scanner_direction == 1:
                if self.scanner_position >= self.SCANNER_WIDTH - 1:
                    self.scanner_direction = -1
                    self.scanner_position = max(0, self.SCANNER_WIDTH - 1)
                else:
                    self.scanner_position += 1
            else:  # scanner_direction == -1
                if self.scanner_position <= 0:
                    self.scanner_direction = 1
                    self.scanner_position = 0
                else:
                    self.scanner_position -= 1
            
            if not (0 <= self.scanner_position < self.SCANNER_WIDTH) and self.SCANNER_WIDTH > 0:
                 self.scanner_position = self.scanner_position % self.SCANNER_WIDTH
            return "".join(current_display_chars)
        else:
            # DEFAULT (ASCII/original unicode_palette) animation logic
            frame = self.default_spinner_frames[self.frame_idx]
            self.frame_idx = (self.frame_idx + 1) % len(self.default_spinner_frames)
            Spinner.last_frame_idx = self.frame_idx
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

        if not self.visible or now - self.last_update < 0.1: # Animation speed
            return

        self.last_update = now
        frame_str = self._next_frame()
        
        max_spinner_width = self.console.width - 2
        if max_spinner_width < 0: max_spinner_width = 0

        current_text_payload_str = f" {self.text}"

        # Construct Rich Text object for the line
        text_line_obj = Text(frame_str)
        if self.config.color != "default" and self.config.color:
            payload_part = Text(current_text_payload_str, style=self.config.color)
        else:
            payload_part = Text(current_text_payload_str)
        text_line_obj.append(payload_part)

        # Truncate based on visual width
        text_line_obj.truncate(max_spinner_width, overflow="crop")
        
        # Render the Rich Text object to a string with ANSI codes using a temporary console
        temp_buffer = StringIO()
        # Ensure the temporary console inherits properties for consistent rendering
        temp_console = Console(
            file=temp_buffer,
            width=self.console.width, # Use main console's width for consistent truncation behavior
            color_system=self.console.color_system,
            force_terminal=self.is_tty, # Important for color output
            # theme=self.console.theme # Avoid AttributeError if self.console has no theme
        )
        temp_console.print(text_line_obj, end="")
        rendered_text_line_str = temp_buffer.getvalue()
        
        # Use visual length for padding and cursor logic
        len_line_to_display = text_line_obj.cell_len 

        padding_to_clear = " " * max(0, self.last_display_len - len_line_to_display)
        
        sys.stdout.write(f"\r{rendered_text_line_str}{padding_to_clear}")
        self.last_display_len = len_line_to_display # Store visual length
        
        # total_chars_written_on_line should be based on visual length for cursor math
        total_chars_written_on_line = len_line_to_display + len(padding_to_clear)
        scan_char_abs_pos = -1

        if self.use_kitt_animation:
            # For KITT, cursor should ideally be at the scanner head's position.
            # self.scanner_position is the index within the KITT frame.
            scan_char_abs_pos = self.scanner_position
        else:
            # For default spinner, find the scan char.
            scan_char_abs_pos = frame_str.find(self.default_spinner_scan_char)

        if scan_char_abs_pos != -1:
            num_backspaces = total_chars_written_on_line - scan_char_abs_pos
            if num_backspaces > 0 : # only backspace if cursor needs to move left
                 sys.stdout.write("\b" * num_backspaces)
        # If scan_char_abs_pos is -1 (e.g. scan char not found or KITT logic places cursor at end),
        # or if num_backspaces is <=0, cursor remains at the end of the written line.

        sys.stdout.flush()

    def end(self) -> None:
        if self.visible and self.is_tty:
            # Use self.animation_len which is set in __init__ based on style
            clear_len = self.last_display_len 
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
    spinner = Spinner("Running spinner...", config=SpinnerConfig())
    for _ in range(100):
        time.sleep(0.15)
        spinner.step()
    spinner.end()
    print("Success!")


if __name__ == "__main__":
    main()
