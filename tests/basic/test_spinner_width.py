import io
import unittest
from unittest.mock import patch

from rich.cells import cell_len
from rich.console import Console

from aider.waiting import Spinner


class TestSpinnerWidth(unittest.TestCase):
    def test_spinner_uses_display_cells(self):
        for text in ["模型名称很长很长", "e\u0301" * 12, "plain ascii text"]:
            with self.subTest(text=text):
                output = io.StringIO()
                with patch.object(Spinner, "_supports_unicode", return_value=False):
                    spinner = Spinner(text)
                spinner.is_tty = True
                spinner.console = Console(file=output, width=20, force_terminal=False)
                spinner.start_time = 0
                spinner.frame_idx = 0
                with patch("sys.stdout", output), patch("aider.waiting.time.time", return_value=1):
                    spinner.step()
                    rendered = output.getvalue()
                    line, backspaces = rendered[1:].split("\b", 1)
                    columns = cell_len(line)
                    self.assertLessEqual(columns, 18)
                    self.assertEqual(spinner.last_display_len, columns)
                    self.assertEqual(len(backspaces) + 1, columns)
                    output.seek(0)
                    output.truncate()
                    spinner.end()
                    self.assertEqual(output.getvalue(), "\r" + " " * columns + "\r")
