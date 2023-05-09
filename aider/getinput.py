import re
from prompt_toolkit.styles import Style

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory

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


import sys
import time
import random

def get_input(history_file, fnames):
    if not sys.stdin.isatty():
        input_line = input()
        print("> ", end="")
        for char in input_line:
            print(char, end="", flush=True)
            time.sleep(random.uniform(0.05, 0.2))
        print()
        return input_line
    inp = ""
    multiline_input = False

    style = Style.from_dict({"": "green"})

    while True:
        completer_instance = FileContentCompleter(fnames)
        if multiline_input:
            show = ". "
        else:
            show = "> "

        try:
            line = prompt(
                show,
                completer=completer_instance,
                history=FileHistory(history_file),
                style=style,
            )
        except EOFError:
            return
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
