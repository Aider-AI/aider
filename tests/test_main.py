import os
import sys
import tempfile
from contextlib import redirect_stdout
from unittest import TestCase
from aider.main import main

class TestMain(TestCase):
    def test_main_with_dev_null(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            with open(os.devnull, 'w') as dev_null:
                with redirect_stdout(dev_null):
                    main()
