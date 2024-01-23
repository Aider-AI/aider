#!/usr/bin/env python

import io
import time

from rich.console import Console
from rich.markdown import Markdown

from aider.dump import dump  # noqa: F401

_text = """
# Header

Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.



## Sub header

- List 1
- List 2
- List me
- List you



```python
import sys

def greeting():
    print("Hello world!")
```

## Sub header too

The end.

"""  # noqa: E501


def showit(lines):
    return

    num_lines = len(lines)
    d = 10
    if num_lines < d:
        start = 0
    else:
        start = num_lines - d

    print("-" * 50)
    for i in range(start, num_lines):
        line = repr(lines[i])[:70]
        print(f"{i:02d}:{line}")
    print("-" * 50)


class MarkdownStream:
    def __init__(self):
        self.printed = []
        self.when = 0

    def update(self, text, final=False, min_delay=0.100):
        now = time.time()
        if not final and now - self.when < min_delay:
            return
        self.when = now

        string_io = io.StringIO()
        console = Console(file=string_io, force_terminal=True)

        markdown = Markdown(text)
        console.print(markdown)
        output = string_io.getvalue()

        lines = output.splitlines(keepends=True)
        num_lines = len(lines)
        if not final:
            num_lines -= 4

        if num_lines <= 1:
            return

        num_printed = len(self.printed)

        """
        if lines[:num_printed] != self.printed:
            dump(repr(text))
            print('xxx')
            print(''.join(self.printed))
            print('xxx')
            print(''.join(lines))
            print('xxx')
            sys.exit()
        """

        show = num_lines - num_printed

        if show <= 0:
            return

        show = lines[num_printed:num_lines]
        print("".join(show), end="")

        self.printed = lines[:num_lines]


if __name__ == "__main__":
    _text = 5 * _text

    pm = MarkdownStream()
    for i in range(6, len(_text)):
        pm.update(_text[:i])
        # time.sleep(0.001)

    pm.update(_text, final=True)
