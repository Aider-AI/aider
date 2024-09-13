import base64
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from prompt_toolkit.completion import Completer, Completion, ThreadedCompleter
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.shortcuts import CompleteStyle, PromptSession
from prompt_toolkit.styles import Style
from pygments.lexers import MarkdownLexer, guess_lexer_for_filename
from pygments.token import Token
from rich.console import Console
from rich.style import Style as RichStyle
from rich.text import Text
from rich.markdown import Markdown
from aider.mdstream import MarkdownStream

from .dump import dump  # noqa: F401
from .utils import is_image_file


@dataclass
class ConfirmGroup:
    preference: str = None
    show_group: bool = True

    def __init__(self, items=None):
        if items is not None:
            self.show_group = len(items) > 1


class AutoCompleter(Completer):
    def __init__(
        self, root, rel_fnames, addable_rel_fnames, commands, encoding, abs_read_only_fnames=None
    ):
        self.addable_rel_fnames = addable_rel_fnames
        self.rel_fnames = rel_fnames
        self.encoding = encoding
        self.abs_read_only_fnames = abs_read_only_fnames or []

        fname_to_rel_fnames = defaultdict(list)
        for rel_fname in addable_rel_fnames:
            fname = os.path.basename(rel_fname)
            if fname != rel_fname:
                fname_to_rel_fnames[fname].append(rel_fname)
        self.fname_to_rel_fnames = fname_to_rel_fnames

        self.words = set()

        self.commands = commands
        self.command_completions = dict()
        if commands:
            self.command_names = self.commands.get_commands()

        for rel_fname in addable_rel_fnames:
            self.words.add(rel_fname)

        for rel_fname in rel_fnames:
            self.words.add(rel_fname)

        all_fnames = [Path(root) / rel_fname for rel_fname in rel_fnames]
        if abs_read_only_fnames:
            all_fnames.extend(abs_read_only_fnames)

        self.all_fnames = all_fnames
        self.tokenized = False

    def tokenize(self):
        if self.tokenized:
            return
        self.tokenized = True

        for fname in self.all_fnames:
            try:
                with open(fname, "r", encoding=self.encoding) as f:
                    content = f.read()
            except (FileNotFoundError, UnicodeDecodeError, IsADirectoryError):
                continue
            try:
                lexer = guess_lexer_for_filename(fname, content)
            except Exception:  # On Windows, bad ref to time.clock which is deprecated
                continue

            tokens = list(lexer.get_tokens(content))
            self.words.update(
                (token[1], f"`{token[1]}`") for token in tokens if token[0] in Token.Name
            )

    def get_command_completions(self, text, words):
        candidates = []
        if len(words) == 1 and not text[-1].isspace():
            partial = words[0].lower()
            candidates = [cmd for cmd in self.command_names if cmd.startswith(partial)]
            return candidates

        if len(words) <= 1:
            return []
        if text[-1].isspace():
            return []

        cmd = words[0]
        partial = words[-1].lower()

        matches, _, _ = self.commands.matching_commands(cmd)
        if len(matches) == 1:
            cmd = matches[0]
        elif cmd not in matches:
            return

        if cmd not in self.command_completions:
            candidates = self.commands.get_completions(cmd)
            self.command_completions[cmd] = candidates
        else:
            candidates = self.command_completions[cmd]

        if candidates is None:
            return

        candidates = [word for word in candidates if partial in word.lower()]
        return candidates

    def get_completions(self, document, complete_event):
        self.tokenize()

        text = document.text_before_cursor
        words = text.split()
        if not words:
            return

        if text and text[-1].isspace():
            # don't keep completing after a space
            return

        if text[0] == "/":
            candidates = self.get_command_completions(text, words)
            if candidates is not None:
                for candidate in sorted(candidates):
                    yield Completion(candidate, start_position=-len(words[-1]))
                return

        candidates = self.words
        candidates.update(set(self.fname_to_rel_fnames))
        candidates = [word if type(word) is tuple else (word, word) for word in candidates]

        last_word = words[-1]
        completions = []
        for word_match, word_insert in candidates:
            if word_match.lower().startswith(last_word.lower()):
                completions.append((word_insert, -len(last_word), word_match))

                rel_fnames = self.fname_to_rel_fnames.get(word_match, [])
                if rel_fnames:
                    for rel_fname in rel_fnames:
                        completions.append((rel_fname, -len(last_word), rel_fname))

        for ins, pos, match in sorted(completions):
            yield Completion(ins, start_position=pos, display=match)


class InputOutput:
    num_error_outputs = 0
    num_user_asks = 0

    def __init__(
        self,
        pretty=True,
        yes=None,
        input_history_file=None,
        chat_history_file=None,
        input=None,
        output=None,
        user_input_color="blue",
        tool_output_color=None,
        tool_error_color="red",
        tool_warning_color="#FFA500",
        assistant_output_color="blue",
        code_theme="default",
        encoding="utf-8",
        dry_run=False,
        llm_history_file=None,
        editingmode=EditingMode.EMACS,
    ):
        self.editingmode = editingmode
        no_color = os.environ.get("NO_COLOR")
        if no_color is not None and no_color != "":
            pretty = False

        self.user_input_color = user_input_color if pretty else None
        self.tool_output_color = tool_output_color if pretty else None
        self.tool_error_color = tool_error_color if pretty else None
        self.tool_warning_color = tool_warning_color if pretty else None
        self.assistant_output_color = assistant_output_color
        self.code_theme = code_theme

        self.input = input
        self.output = output

        self.pretty = pretty
        if self.output:
            self.pretty = False

        self.yes = yes

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

        self.prompt_session = None
        if self.pretty:
            # Initialize PromptSession
            session_kwargs = {
                "input": self.input,
                "output": self.output,
                "lexer": PygmentsLexer(MarkdownLexer),
                "editing_mode": self.editingmode,
            }
            if self.input_history_file is not None:
                session_kwargs["history"] = FileHistory(self.input_history_file)
            try:
                self.prompt_session = PromptSession(**session_kwargs)
                self.console = Console()  # pretty console
            except Exception as err:
                self.console = Console(force_terminal=False, no_color=True)
                self.tool_error(f"Can't initialize prompt toolkit: {err}")  # non-pretty
        else:
            self.console = Console(force_terminal=False, no_color=True)  # non-pretty

    def read_image(self, filename):
        try:
            with open(str(filename), "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
                return encoded_string.decode("utf-8")
        except OSError as err:
            self.tool_error(f"{filename}: unable to read: {err}")
            return
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
        except OSError as err:
            self.tool_error(f"{filename}: unable to read: {err}")
            return
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
        try:
            with open(str(filename), "w", encoding=self.encoding) as f:
                f.write(content)
        except OSError as err:
            self.tool_error(f"Unable to write file {filename}: {err}")

    def rule(self):
        if self.pretty:
            style = dict(style=self.user_input_color) if self.user_input_color else dict()
            self.console.rule(**style)
        else:
            print()

    def get_input(
        self,
        root,
        rel_fnames,
        addable_rel_fnames,
        commands,
        abs_read_only_fnames=None,
        edit_format=None,
    ):
        self.rule()

        rel_fnames = list(rel_fnames)
        show = ""
        if rel_fnames:
            show = " ".join(rel_fnames) + "\n"
        if edit_format:
            show += edit_format
        show += "> "

        inp = ""
        multiline_input = False

        if self.user_input_color and self.pretty:
            style = Style.from_dict(
                {
                    "": self.user_input_color,
                    "pygments.literal.string": f"bold italic {self.user_input_color}",
                }
            )
        else:
            style = None

        completer_instance = ThreadedCompleter(
            AutoCompleter(
                root,
                rel_fnames,
                addable_rel_fnames,
                commands,
                self.encoding,
                abs_read_only_fnames=abs_read_only_fnames,
            )
        )

        kb = KeyBindings()

        @kb.add("escape", "c-m", eager=True)
        def _(event):
            event.current_buffer.insert_text("\n")

        while True:
            if multiline_input:
                show = ". "

            try:
                if self.prompt_session:
                    line = self.prompt_session.prompt(
                        show,
                        completer=completer_instance,
                        reserve_space_for_menu=4,
                        complete_style=CompleteStyle.MULTI_COLUMN,
                        style=style,
                        key_bindings=kb,
                    )
                else:
                    line = input(show)
            except UnicodeEncodeError as err:
                self.tool_error(str(err))
                return ""

            if line and line[0] == "{" and not multiline_input:
                multiline_input = True
                inp += line[1:] + "\n"
                continue
            elif line and line[-1] == "}" and multiline_input:
                inp += line[:-1] + "\n"
                break
            elif multiline_input:
                inp += line + "\n"
            else:
                inp = line
                break

        print()
        self.user_input(inp)
        return inp

    def add_to_input_history(self, inp):
        if not self.input_history_file:
            return
        FileHistory(self.input_history_file).append_string(inp)
        # Also add to the in-memory history if it exists
        if hasattr(self, "session") and hasattr(self.session, "history"):
            self.session.history.append_string(inp)

    def get_input_history(self):
        if not self.input_history_file:
            return []

        fh = FileHistory(self.input_history_file)
        return fh.load_history_strings()

    def log_llm_history(self, role, content):
        if not self.llm_history_file:
            return
        timestamp = datetime.now().isoformat(timespec="seconds")
        with open(self.llm_history_file, "a", encoding=self.encoding) as log_file:
            log_file.write(f"{role.upper()} {timestamp}\n")
            log_file.write(content + "\n")

    def user_input(self, inp, log_only=True):
        if not log_only:
            if self.pretty and self.user_input_color:
                style = dict(style=self.user_input_color)
            else:
                style = dict()

            self.console.print(Text(inp), **style)

        prefix = "####"
        if inp:
            hist = inp.splitlines()
        else:
            hist = ["<blank>"]

        hist = f"  \n{prefix} ".join(hist)

        hist = f"""
{prefix} {hist}"""
        self.append_chat_history(hist, linebreak=True)

    # OUTPUT

    def ai_output(self, content):
        hist = "\n" + content.strip() + "\n\n"
        self.append_chat_history(hist)

    def confirm_ask(
        self, question, default="y", subject=None, explicit_yes_required=False, group=None
    ):
        self.num_user_asks += 1

        if group and not group.show_group:
            group = None

        valid_responses = ["yes", "no"]
        options = " (Y)es/(N)o"
        if group:
            if not explicit_yes_required:
                options += "/(A)ll"
                valid_responses.append("all")
            options += "/(S)kip all"
            valid_responses.append("skip")
        question += options + " [Yes]: "

        if subject:
            self.tool_output()
            if "\n" in subject:
                lines = subject.splitlines()
                max_length = max(len(line) for line in lines)
                padded_lines = [line.ljust(max_length) for line in lines]
                padded_subject = "\n".join(padded_lines)
                self.tool_output(padded_subject, bold=True)
            else:
                self.tool_output(subject, bold=True)

        if self.pretty and self.user_input_color:
            style = {"": self.user_input_color}
        else:
            style = dict()

        def is_valid_response(text):
            if not text:
                return True
            return text.lower() in valid_responses

        if self.yes is True:
            res = "n" if explicit_yes_required else "y"
        elif self.yes is False:
            res = "n"
        elif group and group.preference:
            res = group.preference
            self.user_input(f"{question}{res}", log_only=False)
        else:
            while True:
                if self.prompt_session:
                    res = self.prompt_session.prompt(
                        question,
                        style=Style.from_dict(style),
                    )
                else:
                    res = input(question)

                if not res:
                    res = "y"  # Default to Yes if no input
                    break
                res = res.lower()
                good = any(valid_response.startswith(res) for valid_response in valid_responses)
                if good:
                    break

                error_message = f"Please answer with one of: {', '.join(valid_responses)}"
                self.tool_error(error_message)

        res = res.lower()[0]

        if explicit_yes_required:
            is_yes = res == "y"
        else:
            is_yes = res in ("y", "a")

        is_all = res == "a" and group is not None and not explicit_yes_required
        is_skip = res == "s" and group is not None

        if group:
            if is_all and not explicit_yes_required:
                group.preference = "all"
            elif is_skip:
                group.preference = "skip"

        hist = f"{question.strip()} {res}"
        self.append_chat_history(hist, linebreak=True, blockquote=True)

        return is_yes

    def prompt_ask(self, question, default="", subject=None):
        self.num_user_asks += 1

        if subject:
            self.tool_output()
            self.tool_output(subject, bold=True)

        if self.pretty and self.user_input_color:
            style = Style.from_dict({"": self.user_input_color})
        else:
            style = None

        if self.yes is True:
            res = "yes"
        elif self.yes is False:
            res = "no"
        else:
            if self.prompt_session:
                res = self.prompt_session.prompt(question + " ", default=default, style=style)
            else:
                res = input(question + " ")

        hist = f"{question.strip()} {res.strip()}"
        self.append_chat_history(hist, linebreak=True, blockquote=True)
        if self.yes in (True, False):
            self.tool_output(hist)

        return res

    def _tool_message(self, message="", strip=True, color=None):
        if message.strip():
            if "\n" in message:
                for line in message.splitlines():
                    self.append_chat_history(line, linebreak=True, blockquote=True, strip=strip)
            else:
                hist = message.strip() if strip else message
                self.append_chat_history(hist, linebreak=True, blockquote=True)

        message = Text(message)
        style = dict(style=color) if self.pretty and color else dict()
        self.console.print(message, **style)

    def tool_error(self, message="", strip=True):
        self.num_error_outputs += 1
        self._tool_message(message, strip, self.tool_error_color)

    def tool_warning(self, message="", strip=True):
        self._tool_message(message, strip, self.tool_warning_color)

    def tool_output(self, *messages, log_only=False, bold=False):
        if messages:
            hist = " ".join(messages)
            hist = f"{hist.strip()}"
            self.append_chat_history(hist, linebreak=True, blockquote=True)

        if log_only:
            return

        messages = list(map(Text, messages))
        style = dict()
        if self.pretty:
            if self.tool_output_color:
                style["color"] = self.tool_output_color
            style["reverse"] = bold

        style = RichStyle(**style)
        self.console.print(*messages, style=style)

    def assistant_output(self, message, stream=False):
        mdStream = None
        show_resp = message
        
        if self.pretty:
            if stream:
                mdargs = dict(style=self.assistant_output_color, code_theme=self.code_theme)
                mdStream = MarkdownStream(mdargs=mdargs)
            else:
                show_resp = Markdown(
                    message, style=self.assistant_output_color, code_theme=self.code_theme
                )
        else:
            show_resp = Text(message or "<no response>")

        self.console.print(show_resp)
        return mdStream
        
    def print(self, message=""):
        print(message)
        
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
            try:
                with self.chat_history_file.open("a", encoding=self.encoding) as f:
                    f.write(text)
            except (PermissionError, OSError):
                self.tool_error(
                    f"Warning: Unable to write to chat history file {self.chat_history_file}."
                    " Permission denied."
                )
                self.chat_history_file = None  # Disable further attempts to write
