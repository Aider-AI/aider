import os
from pygments.lexers import guess_lexer_for_filename
from pygments.token import Token
from prompt_toolkit.styles import Style
from pygments.util import ClassNotFound
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import CompleteStyle
from rich.console import Console
from rich.text import Text
import sys
import time
import random


class FileContentCompleter(Completer):
    def __init__(self, fnames, commands):
        self.commands = commands

        self.words = set()
        for fname in fnames:
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

        last_word = words[-1]
        for word in candidates:
            if word.lower().startswith(last_word.lower()):
                yield Completion(word, start_position=-len(last_word))


class InputOutput:
    def __init__(self, pretty, yes):
        self.pretty = pretty
        self.yes = yes

        if pretty:
            self.console = Console()
        else:
            self.console = Console(force_terminal=True, no_color=True)

    def tool_error(self, message):
        message = Text(message)
        self.console.print('[red]', message)

    def canned_input(self, show_prompt):
        console = Console()

        input_line = input()

        console.print(show_prompt, end="", style="green")
        for char in input_line:
            console.print(char, end="", style="green")
            time.sleep(random.uniform(0.01, 0.15))
        console.print()
        console.print()
        return input_line

    def get_input(self, history_file, fnames, commands):
        fnames = list(fnames)
        if len(fnames) > 1:
            common_prefix = os.path.commonpath(fnames)
            if not common_prefix.endswith(os.path.sep):
                common_prefix += os.path.sep
            short_fnames = [fname.replace(common_prefix, "", 1) for fname in fnames]
        elif len(fnames):
            short_fnames = [os.path.basename(fnames[0])]
        else:
            short_fnames = []

        show = " ".join(short_fnames)
        if len(show) > 10:
            show += "\n"
        show += "> "

        if not sys.stdin.isatty():
            return self.canned_input(show)

        inp = ""
        multiline_input = False

        style = Style.from_dict({"": "green"})

        while True:
            completer_instance = FileContentCompleter(fnames, commands)
            if multiline_input:
                show = ". "

            line = prompt(
                show,
                completer=completer_instance,
                history=FileHistory(history_file),
                style=style,
                reserve_space_for_menu=4,
                complete_style=CompleteStyle.MULTI_COLUMN,
            )
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
        return inp

    def confirm_ask(self, question, default="y"):
        if self.yes:
            return True
        return prompt(question + " ", default=default)

    def prompt_ask(self, question, default=None):
        if self.yes:
            return True
        return prompt(question + " ", default=default)
