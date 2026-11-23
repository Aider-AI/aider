import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from aider.copypaste import ClipboardWatcher


class TestClipboardWatcher(unittest.TestCase):
    def test_transient_clipboard_error_waits_before_retrying(self):
        io = MagicMock()
        recovered = threading.Event()
        io.interrupt_input.side_effect = recovered.set
        watcher = ClipboardWatcher(io)
        polls = []
        calls = 0

        def paste():
            nonlocal calls
            calls += 1
            if calls == 1:
                return "initial"
            polls.append(time.monotonic())
            if calls == 2:
                raise RuntimeError("clipboard temporarily unavailable")
            return "updated\ntext"

        with patch("aider.copypaste.pyperclip.paste", side_effect=paste):
            try:
                watcher.start()
                self.assertTrue(recovered.wait(5), "clipboard watcher did not recover")
            finally:
                watcher.stop()

        self.assertGreaterEqual(polls[1] - polls[0], 0.4)
        self.assertEqual(io.placeholder, "\nupdated\ntext\n")
        io.interrupt_input.assert_called_once()
