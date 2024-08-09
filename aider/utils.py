import itertools
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import git

from aider.dump import dump  # noqa: F401

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}


class IgnorantTemporaryDirectory:
    def __init__(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def __enter__(self):
        return self.temp_dir.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        try:
            self.temp_dir.cleanup()
        except (OSError, PermissionError):
            pass  # Ignore errors (Windows)

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
        os.chdir(self.temp_dir.name)
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
        output.append("")
        role = msg["role"].upper()
        content = msg.get("content")
        if isinstance(content, list):  # Handle list content (e.g., image messages)
            for item in content:
                if isinstance(item, dict) and "image_url" in item:
                    output.append(f"{role} Image URL: {item['image_url']['url']}")
        elif isinstance(content, str):  # Handle string content
            output.append(format_content(role, content))
        content = msg.get("function_call")
        if content:
            output.append(f"{role} {content}")

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
    ]
    cmd += args
    return cmd


def run_install(cmd):
    print()
    print("Installing: ", " ".join(cmd))

    try:
        output = []
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
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
    spinner_chars = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])

    def __init__(self, text):
        self.text = text
        self.start_time = time.time()
        self.last_update = 0
        self.visible = False

    def step(self):
        current_time = time.time()
        if not self.visible and current_time - self.start_time >= 0.5:
            self.visible = True
            self._step()
        elif self.visible and current_time - self.last_update >= 0.1:
            self._step()
        self.last_update = current_time

    def _step(self):
        if not self.visible:
            return

        print(f"\r{self.text} {next(self.spinner_chars)}\r{self.text} ", end="", flush=True)

    def end(self):
        if self.visible:
            print("\r" + " " * (len(self.text) + 3))


def check_pip_install_extra(io, module, prompt, pip_install_cmd):
    try:
        __import__(module)
        return True
    except (ImportError, ModuleNotFoundError):
        pass

    cmd = get_pip_install(pip_install_cmd)

    text = f"{prompt}:\n\n{' '.join(cmd)}\n"
    io.tool_error(text)

    if not io.confirm_ask("Run pip install?", default="y"):
        return

    success, output = run_install(cmd)
    if success:
        try:
            __import__(module)
            return True
        except (ImportError, ModuleNotFoundError) as err:
            io.tool_error(str(err))
            pass

    io.tool_error(output)

    print()
    print(f"Failed to install {pip_install_cmd[0]}")
