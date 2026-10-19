import runpy
from unittest import TestCase
from unittest.mock import patch


class TestMainModule(TestCase):
    def test_main_return_code_is_exit_status(self):
        with patch("aider.main.main", return_value=7):
            with self.assertRaises(SystemExit) as exc:
                runpy.run_module("aider", run_name="__main__")

        self.assertEqual(exc.exception.code, 7)