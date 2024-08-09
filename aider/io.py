import base64
from datetime import datetime
from pathlib import Path

from prompt_toolkit.history import FileHistory

from .dump import dump  # noqa: F401
from .utils import is_image_file


class InputOutput:
    num_error_outputs = 0
    num_user_asks = 0
    
    def __init__(
        self,
        input_history_file=None,
        chat_history_file=None,
        encoding="utf-8",
        dry_run=False,
        llm_history_file=None,
    ):
        
        self.input_history_file = input_history_file
        self.llm_history_file = llm_history_file
        if chat_history_file is not None:
            self.chat_history_file = Path(chat_history_file)
        else:
            self.chat_history_file = None

        self.encoding = encoding
        self.dry_run = dry_run

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.append_chat_history(f"\n# aider chat started at {current_time}\n\n")

    def read_image(self, filename):
        try:
            with open(str(filename), "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
                return encoded_string.decode("utf-8")
        except FileNotFoundError:
            self.tool_error(f"{filename}: file not found error")
            return
        except IsADirectoryError:
            self.tool_error(f"{filename}: is a directory")
            return
        except Exception as e:
            self.tool_error(f"{filename}: {e}")
            return

    def read_text(self, filename):
        if is_image_file(filename):
            return self.read_image(filename)

        try:
            with open(str(filename), "r", encoding=self.encoding) as f:
                return f.read()
        except FileNotFoundError:
            self.tool_error(f"{filename}: file not found error")
            return
        except IsADirectoryError:
            self.tool_error(f"{filename}: is a directory")
            return
        except UnicodeError as e:
            self.tool_error(f"{filename}: {e}")
            self.tool_error("Use --encoding to set the unicode encoding.")
            return

    def write_text(self, filename, content):
        if self.dry_run:
            return
        with open(str(filename), "w", encoding=self.encoding) as f:
            f.write(content)

    def get_input(self, root, rel_fnames, addable_rel_fnames, commands):
        return ""

    def add_to_input_history(self, inp):
        if not self.input_history_file:
            return
        FileHistory(self.input_history_file).append_string(inp)

    def get_input_history(self):
        if not self.input_history_file:
            return []

        fh = FileHistory(self.input_history_file)
        return fh.load_history_strings()
    
    def get_history_file(self):
        FileHistory(self.input_history_file)
        
    def log_llm_history(self, role, content):
        if not self.llm_history_file:
            return
        timestamp = datetime.now().isoformat(timespec="seconds")
        with open(self.llm_history_file, "a", encoding=self.encoding) as log_file:
            log_file.write(f"{role.upper()} {timestamp}\n")
            log_file.write(content + "\n")

    def user_input(self, inp, log_only=True):
        return
    
    # OUTPUT

    def ai_output(self, content):
        hist = "\n" + content.strip() + "\n\n"
        self.append_chat_history(hist)

    def confirm_ask(self, question, default="y"):
        return False

    def prompt_ask(self, question, default=None):
        return "no"

    def tool_error(self, message="", strip=True):
        self.num_error_outputs += 1
        
        if message.strip():
            if "\n" in message:
                for line in message.splitlines():
                    self.append_chat_history(line, linebreak=True, blockquote=True, strip=strip)
            else:
                if strip:
                    hist = message.strip()
                else:
                    hist = message
                self.append_chat_history(hist, linebreak=True, blockquote=True)

    def tool_output(self, *messages, log_only=False):
        if messages:
            hist = " ".join(messages)
            hist = f"{hist.strip()}"
            self.append_chat_history(hist, linebreak=True, blockquote=True)

    def append_chat_history(self, text, linebreak=False, blockquote=False, strip=True):
        if blockquote:
            if strip:
                text = text.strip()
            text = "> " + text
        if linebreak:
            if strip:
                text = text.rstrip()
            text = text + "  \n"
        if not text.endswith("\n"):
            text += "\n"
        if self.chat_history_file is not None:
            with self.chat_history_file.open("a", encoding=self.encoding) as f:
                f.write(text)
