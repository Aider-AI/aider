#!/usr/bin/env python

"""
Thread-based, killable spinner utility.

Use it like:

    from aider.waiting import WaitingSpinner

    spinner = WaitingSpinner("Waiting for LLM")
    spinner.start()
    ...  # long task
    spinner.stop()
"""

import sys
import threading
import time

from rich.console import Console


class Spinner:
    """
    Minimal spinner that scans a single marker back and forth across a line.

    The animation is pre-rendered into a list of frames.  If the terminal
    cannot display unicode the frames are converted to plain ASCII.
    """

    last_frame_idx = 0  # Class variable to store the last frame index

    def __init__(self, text: str, width: int = 7):
        self.text = text
        self.start_time = time.time()
        self.last_update = 0.0
        self.visible = False
        self.is_tty = sys.stdout.isatty()
        self.console = Console()

        # Pre-render the animation frames using pure ASCII so they will
        # always display, even on very limited terminals.
        ascii_frames = [
            "#=        ",  # C1 C2 space(8)
            "=#        ",  # C2 C1 space(8)
            " =#       ",  # space(1) C2 C1 space(7)
            "  =#      ",  # space(2) C2 C1 space(6)
            "   =#     ",  # space(3) C2 C1 space(5)
            "    =#    ",  # space(4) C2 C1 space(4)
            "     =#   ",  # space(5) C2 C1 space(3)
            "      =#  ",  # space(6) C2 C1 space(2)
            "       =# ",  # space(7) C2 C1 space(1)
            "        =#",  # space(8) C2 C1
            "        #=",  # space(8) C1 C2
            "       #= ",  # space(7) C1 C2 space(1)
            "      #=  ",  # space(6) C1 C2 space(2)
            "     #=   ",  # space(5) C1 C2 space(3)
            "    #=    ",  # space(4) C1 C2 space(4)
            "   #=     ",  # space(3) C1 C2 space(5)
            "  #=      ",  # space(2) C1 C2 space(6)
            " #=       ",  # space(1) C1 C2 space(7)
        ]

        self.unicode_palette = "░█"
        xlate_from, xlate_to = ("=#", self.unicode_palette)

        # If unicode is supported, swap the ASCII chars for nicer glyphs.
        if self._supports_unicode():
            translation_table = str.maketrans(xlate_from, xlate_to)
            frames = [f.translate(translation_table) for f in ascii_frames]
            self.scan_char = xlate_to[xlate_from.find("#")]
        else:
            frames = ascii_frames
            self.scan_char = "#"

        # Bounce the scanner back and forth.
        self.frames = frames
        self.frame_idx = Spinner.last_frame_idx  # Initialize from class variable
        self.width = len(frames[0]) - 2  # number of chars between the brackets
        self.animation_len = len(frames[0])
        self.last_display_len = 0  # Length of the last spinner line (frame + text)

    def _supports_unicode(self) -> bool:
        if not self.is_tty:
            return False
        try:
            out = self.unicode_palette
            out += "\b" * len(self.unicode_palette)
            out += " " * len(self.unicode_palette)
            out += "\b" * len(self.unicode_palette)
            sys.stdout.write(out)
            sys.stdout.flush()
            return True
        except UnicodeEncodeError:
            return False
        except Exception:
            return False

    def _next_frame(self) -> str:
        frame = self.frames[self.frame_idx]
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        Spinner.last_frame_idx = self.frame_idx  # Update class variable
        return frame

    def step(self, text: str = None) -> None:
        if text is not None:
            self.text = text

        if not self.is_tty:
            return

        now = time.time()
        if not self.visible and now - self.start_time >= 0.5:
            self.visible = True
            self.last_update = 0.0
            if self.is_tty:
                self.console.show_cursor(False)

        if not self.visible or now - self.last_update < 0.1:
            return

        self.last_update = now
        frame_str = self._next_frame()

        # Determine the maximum width for the spinner line
        # Subtract 2 as requested, to leave a margin or prevent cursor wrapping issues
        max_spinner_width = self.console.width - 2
        if max_spinner_width < 0:  # Handle extremely narrow terminals
            max_spinner_width = 0

        current_text_payload = f" {self.text}"
        line_to_display = f"{frame_str}{current_text_payload}"

        # Truncate the line if it's too long for the console width
        if len(line_to_display) > max_spinner_width:
            line_to_display = line_to_display[:max_spinner_width]

        len_line_to_display = len(line_to_display)

        # Calculate padding to clear any remnants from a longer previous line
        padding_to_clear = " " * max(0, self.last_display_len - len_line_to_display)

        # Write the spinner frame, text, and any necessary clearing spaces
        sys.stdout.write(f"\r{line_to_display}{padding_to_clear}")
        self.last_display_len = len_line_to_display

        # Calculate number of backspaces to position cursor at the scanner character
        scan_char_abs_pos = frame_str.find(self.scan_char)

        # Total characters written to the line (frame + text + padding)
        total_chars_written_on_line = len_line_to_display + len(padding_to_clear)

        # num_backspaces will be non-positive if scan_char_abs_pos is beyond
        # total_chars_written_on_line (e.g., if the scan char itself was truncated).
        # (e.g., if the scan char itself was truncated).
        # In such cases, (effectively) 0 backspaces are written,
        # and the cursor stays at the end of the line.
        num_backspaces = total_chars_written_on_line - scan_char_abs_pos
        sys.stdout.write("\b" * num_backspaces)
        sys.stdout.flush()

    def end(self) -> None:
        if self.visible and self.is_tty:
            clear_len = self.last_display_len  # Use the length of the last displayed content
            sys.stdout.write("\r" + " " * clear_len + "\r")
            sys.stdout.flush()
            self.console.show_cursor(True)
        self.visible = False


class WaitingSpinner:
    """Background spinner that can be started/stopped safely."""

    def __init__(self, text: str = "Waiting for LLM", delay: float = 0.15):
        self.spinner = Spinner(text)
        self.delay = delay
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        while not self._stop_event.is_set():
            self.spinner.step()
            time.sleep(self.delay)
        self.spinner.end()

    def start(self):
        """Start the spinner in a background thread."""
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self):
        """Request the spinner to stop and wait briefly for the thread to exit."""
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=self.delay)
        self.spinner.end()

    # Allow use as a context-manager
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def main():
    spinner = Spinner("Running spinner...")
    try:
        for _ in range(100):
            time.sleep(0.15)
            spinner.step()
        print("Success!")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        spinner.end()


if __name__ == "__main__":
    main()
