import os
import unittest
from pathlib import Path
from unittest.mock import patch

from aider.io import AutoCompleter, InputOutput
from aider.utils import ChdirTemporaryDirectory


class TestInputOutput(unittest.TestCase):
    def test_no_color_environment_variable(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            io = InputOutput()
            self.assertFalse(io.pretty)

    def test_autocompleter_with_non_existent_file(self):
        root = ""
        rel_fnames = ["non_existent_file.txt"]
        addable_rel_fnames = []
        commands = None
        autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")
        self.assertEqual(autocompleter.words, set(rel_fnames))

    def test_autocompleter_with_unicode_file(self):
        with ChdirTemporaryDirectory():
            root = ""
            fname = "file.py"
            rel_fnames = [fname]
            addable_rel_fnames = []
            commands = None
            autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")
            self.assertEqual(autocompleter.words, set(rel_fnames))

            Path(fname).write_text("def hello(): pass\n")
            autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")
            self.assertEqual(autocompleter.words, set(rel_fnames + ["hello"]))

            encoding = "utf-16"
            some_content_which_will_error_if_read_with_encoding_utf8 = "ÅÍÎÏ".encode(encoding)
            with open(fname, "wb") as f:
                f.write(some_content_which_will_error_if_read_with_encoding_utf8)

            autocompleter = AutoCompleter(root, rel_fnames, addable_rel_fnames, commands, "utf-8")
            self.assertEqual(autocompleter.words, set(rel_fnames))


if __name__ == "__main__":
    unittest.main()
