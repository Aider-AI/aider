#!/usr/bin/env python

import io
import time
from typing import List, Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

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


class MarkdownStream:
    """A class for streaming and rendering markdown content."""

    def __init__(self, mdargs: Optional[dict] = None):
        self.printed: List[str] = []
        self.mdargs = mdargs or {}
        self.live: Optional[Live] = Live(Text(""), refresh_per_second=1.0 / self.min_delay)
        self.live.start()
        self.when = 0
        self.min_delay = 0.050
        self.live_window = 6

    def __del__(self):
        if self.live:
            try:
                self.live.stop()
            except Exception:
                pass

    def update(self, text: str, final: bool = False) -> None:
        now = time.time()
        if not final and now - self.when < self.min_delay:
            return
        self.when = now

        string_io = io.StringIO()
        console = Console(file=string_io, force_terminal=True)
        markdown = Markdown(text, **self.mdargs)
        console.print(markdown)
        output = string_io.getvalue()

        lines = output.splitlines(keepends=True)
        num_lines = len(lines)

        if not final:
            num_lines -= self.live_window

        if final or num_lines > 0:
            num_printed = len(self.printed)
            show = num_lines - num_printed

            if show > 0:
                show_lines = lines[num_printed:num_lines]
                show_text = "".join(show_lines)
                show_text = Text.from_ansi(show_text)
                self.live.console.print(show_text)
                self.printed = lines[:num_lines]

        if final:
            self.live.update(Text(""))
            self.live.stop()
            self.live = None
        else:
            rest = lines[num_lines:]
            rest_text = "".join(rest)
            rest_text = Text.from_ansi(rest_text)
            self.live.update(rest_text)


if __name__ == "__main__":
    _text = 5 * _text

    pm = MarkdownStream()
    for i in range(6, len(_text)):
        pm.update(_text[:i])
        time.sleep(0.01)

    pm.update(_text, final=True)
