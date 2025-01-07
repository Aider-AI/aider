#!/usr/bin/env python

import io
import time

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
    """Streaming markdown renderer that progressively displays content with a live updating window.

    Uses rich.console and rich.live to render markdown content with smooth scrolling
    and partial updates. Maintains a sliding window of visible content while streaming
    in new markdown text.
    """

    live = None  # Rich Live display instance
    when = 0  # Timestamp of last update
    min_delay = 0.050  # Minimum time between updates (20fps)
    live_window = 6  # Number of lines to keep visible at bottom during streaming

    def __init__(self, mdargs=None):
        """Initialize the markdown stream.

        Args:
            mdargs (dict, optional): Additional arguments to pass to rich Markdown renderer
        """
        self.printed = []  # Stores lines that have already been printed

        if mdargs:
            self.mdargs = mdargs
        else:
            self.mdargs = dict()

        # Initialize rich Live display with empty text
        self.live = Live(Text(""), refresh_per_second=1.0 / self.min_delay)
        self.live.start()

    def __del__(self):
        """Destructor to ensure Live display is properly cleaned up."""
        if self.live:
            try:
                self.live.stop()
            except Exception:
                pass  # Ignore any errors during cleanup

    def update(self, text, final=False):
        """Update the displayed markdown content.

        Args:
            text (str): New markdown text to append
            final (bool): If True, this is the final update and we should clean up
        """
        now = time.time()
        # Throttle updates to maintain smooth rendering
        if not final and now - self.when < self.min_delay:
            return
        self.when = now

        # Render the markdown to a string buffer
        string_io = io.StringIO()
        console = Console(file=string_io, force_terminal=True)
        markdown = Markdown(text, **self.mdargs)
        console.print(markdown)
        output = string_io.getvalue()

        # Split rendered output into lines
        lines = output.splitlines(keepends=True)
        num_lines = len(lines)

        # During streaming, keep a window of lines at the bottom visible
        if not final:
            num_lines -= self.live_window

        # If we have new content to display...
        if final or num_lines > 0:
            num_printed = len(self.printed)
            show = num_lines - num_printed

            # Skip if no new lines to show
            if show <= 0:
                return

            # Get the new lines and display them
            show = lines[num_printed:num_lines]
            show = "".join(show)
            show = Text.from_ansi(show)
            self.live.console.print(show)

            # Update our record of printed lines
            self.printed = lines[:num_lines]

        # Handle final update cleanup
        if final:
            self.live.update(Text(""))
            self.live.stop()
            self.live = None
        else:
            # Update the live window with remaining lines
            rest = lines[num_lines:]
            rest = "".join(rest)
            rest = Text.from_ansi(rest)
            self.live.update(rest)


if __name__ == "__main__":
    _text = 5 * _text

    pm = MarkdownStream()
    for i in range(6, len(_text)):
        pm.update(_text[:i])
        time.sleep(0.01)

    pm.update(_text, final=True)
