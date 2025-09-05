#!/usr/bin/env python

"""
A simple wrapper for rich.status to provide a spinner.
"""

from rich.console import Console


class Spinner:
    """A wrapper around rich.status.Status for displaying a spinner."""

    def __init__(self, text: str = "Waiting..."):
        self.text = text
        self.console = Console()
        self.status = None

    def step(self, message=None):
        """Start the spinner or update its text."""
        if self.status is None:
            self.status = self.console.status(self.text, spinner="dots2")
            self.status.start()
        elif message:
            self.status.update(message)

    def end(self):
        """Stop the spinner."""
        if self.status:
            self.status.stop()
            self.status = None

    # Allow use as a context-manager
    def __enter__(self):
        self.step()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end()
