import os
import os.path
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token
from prompt_toolkit.styles import Style
from pygments.util import ClassNotFound
from prompt_toolkit.shortcuts import PromptSession, prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import CompleteStyle
from rich.console import Console
from rich.text import Text
from pathlib import Path
from datetime import datetime

from collections import defaultdict


class FileContentCompleter(Completer):
    def __init__(self, root, rel_fnames, addable_rel_fnames, commands):
        self.commands = commands
        self.addable_rel_fnames = addable_rel_fnames
        self.rel_fnames = rel_fnames

        fname_to_rel_fnames = defaultdict(list)
        for rel_fname in addable_rel_fnames:
            fname = os.path.basename(rel_fname)
            if fname != rel_fname:
                fname_to_rel_fnames[fname].append(rel_fname)
        self.fname_to_rel_fnames = fname_to_rel_fnames

        self.words = set()
        for rel_fname in addable_rel_fnames:
            self.words.add(rel_fname)

        for rel_fname in rel_fnames:
            self.words.add(rel_fname)

            fname = os.path.join(root, rel_fname)
            with open(fname, "r") as f:
                content = f.read()
            try:
                lexer = guess_lexer_for_filename(fname, content)
            except ClassNotFound:
                continue
            tokens = list(lexer.get_tokens(content))
            self.words.update(token[1] for token in tokens if token[0] in Token.Name)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()
        if not words:
            return

        if text[0] == "/":
            if len(words) == 1 and not text[-1].isspace():
                candidates = self.commands.get_commands()
            else:
                for completion in self.commands.get_command_completions(words[0][1:], words[-1]):
                    yield completion
                return
        else:
            candidates = self.words
            candidates.update(set(self.fname_to_rel_fnames))

        last_word = words[-1]
        for word in candidates:
            if word.lower().startswith(last_word.lower()):
                rel_fnames = self.fname_to_rel_fnames.get(word, [])
                if rel_fnames:
                    for rel_fname in rel_fnames:
                        yield Completion(rel_fname, start_position=-len(last_word))
                else:
                    yield Completion(word, start_position=-len(last_word))


class InputOutput:
    def __init__(
        self,
        pretty=True,
        yes=False,
        input_history_file=None,
        chat_history_file=None,
        input=None,
        output=None,
        user_input_color="blue",
        tool_output_color=None,
        tool_error_color="red",
    ):
        no_color = os.environ.get("NO_COLOR")
        if no_color is not None and no_color != "":
            pretty = False

        self.user_input_color = user_input_color if pretty else None
        self.tool_output_color = tool_output_color if pretty else None
        self.tool_error_color = tool_error_color if pretty else None
        self.input = input
        self.output = output
        self.pretty = pretty
        self.yes = yes
        self.input_history_file = input_history_file
        if chat_history_file is not None:
            self.chat_history_file = Path(chat_history_file)
        else:
            self.chat_history_file = None

        self.console = Console(force_terminal=not pretty, no_color=not pretty)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.append_chat_history(f"\n# aider chat started at {current_time}\n\n")

    def get_input(self, root, rel_fnames, addable_rel_fnames, commands):
        if self.pretty:
            style = dict(style=self.user_input_color) if self.user_input_color else dict()
            self.console.rule(**style)
        else:
            print()

        rel_fnames = list(rel_fnames)
        show = " ".join(rel_fnames)
        if len(show) > 10:
            show += "\n"
        show += "> "

        inp = ""
        multiline_input = False

        if self.user_input_color:
            style = Style.from_dict({"": self.user_input_color})
        else:
            style = None

        while True:
            completer_instance = FileContentCompleter(
                root, rel_fnames, addable_rel_fnames, commands
            )
            if multiline_input:
                show = ". "

            session_kwargs = {
                "message": show,
                "completer": completer_instance,
                "reserve_space_for_menu": 4,
                "complete_style": CompleteStyle.MULTI_COLUMN,
                "input": self.input,
                "output": self.output,
            }
            if style:
                session_kwargs["style"] = style

            if self.input_history_file is not None:
                session_kwargs["history"] = FileHistory(self.input_history_file)

            session = PromptSession(**session_kwargs)
            line = session.prompt()

            if line.strip() == "{" and not multiline_input:
                multiline_input = True
                continue
            elif line.strip() == "}" and multiline_input:
                break
            elif multiline_input:
                inp += line + "\n"
            else:
                inp = line
                break

        print()

        prefix = "####"
        if inp:
            hist = inp.splitlines()
        else:
            hist = ["<blank>"]

        hist = f"  \n{prefix} ".join(hist)

        hist = f"""
{prefix} {hist}"""
        self.append_chat_history(hist, linebreak=True)

        return inp

    # OUTPUT

    def ai_output(self, content):
        hist = "\n" + content.strip() + "\n\n"
        self.append_chat_history(hist)

    def confirm_ask(self, question, default="y"):
        if self.yes:
            res = "yes"
        else:
            res = prompt(question + " ", default=default)

        hist = f"{question.strip()} {res.strip()}"
        self.append_chat_history(hist, linebreak=True, blockquote=True)

        if not res or not res.strip():
            return
        return res.strip().lower().startswith("y")

    def prompt_ask(self, question, default=None):
        if self.yes:
            res = "yes"
        else:
            res = prompt(question + " ", default=default)

        hist = f"{question.strip()} {res.strip()}"
        self.append_chat_history(hist, linebreak=True, blockquote=True)

        return res

    def tool_error(self, message):
        if message.strip():
            hist = f"{message.strip()}"
            self.append_chat_history(hist, linebreak=True, blockquote=True)

        message = Text(message)
        style = dict(style=self.tool_error_color) if self.tool_error_color else dict()
        self.console.print(message, **style)

    def tool_output(self, *messages, log_only=False):
        if messages:
            hist = " ".join(messages)
            hist = f"{hist.strip()}"
            self.append_chat_history(hist, linebreak=True, blockquote=True)

        if not log_only:
            messages = list(map(Text, messages))
            style = dict(style=self.tool_output_color) if self.tool_output_color else dict()
            self.console.print(*messages, **style)

    def append_chat_history(self, text, linebreak=False, blockquote=False):
        if blockquote:
            text = text.strip()
            text = "> " + text
        if linebreak:
            text = text.rstrip()
            text = text + "  \n"
        if not text.endswith("\n"):
            text += "\n"
        if self.chat_history_file is not None:
            with self.chat_history_file.open("a") as f:
                f.write(text)
