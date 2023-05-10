import os
import re
from pathlib import Path

from prompt_toolkit.styles import Style

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory

from rich.console import Console
import sys
import time
import random


class FileContentCompleter(Completer):
    def __init__(self, fnames):
        self.fnames = fnames

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()
        if not words:
            return

        last_word = words[-1]
        for fname in self.fnames:
            with open(fname, "r") as f:
                content = f.read()

            for word in re.split(r'\W+', content):
                if word.startswith(last_word):
                    yield Completion(word, start_position=-len(last_word))


def canned_input(show_prompt):
    console = Console()

    input_line = input()

    console.print(show_prompt, end="", style="green")
    for char in input_line:
        console.print(char, end="", style="green")
        time.sleep(random.uniform(0.01, 0.15))
    console.print()
    console.print()
    return input_line



def get_input(history_file, fnames):
    fnames = list(fnames)
    if len(fnames) > 1:
        common_prefix = os.path.commonprefix(fnames)
        short_fnames = [fname.replace(common_prefix, '', 1) for fname in fnames]
    else:
        short_fnames = [os.path.basename(fnames[0])]
    show = ' '.join(short_fnames)
    show += "\n> "

    if not sys.stdin.isatty():
        return canned_input(show_prompt)

    inp = ""
    multiline_input = False

    style = Style.from_dict({"": "green"})

    while True:
        completer_instance = FileContentCompleter(fnames)
        if multiline_input:
            show = ". "

        line = prompt(
            show,
            completer=completer_instance,
            history=FileHistory(history_file),
            style=style,
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
