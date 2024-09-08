import unittest
import uuid

from aider.utils import invoke_callback


class BaseUtilsTestCase(unittest.TestCase):
    pass


class InvokeCallbackTestCase(BaseUtilsTestCase):
    def setUp(self):
        self.callback_file = "tests/fixtures/sample_callback.py"
        self.callback_file_not_found = "tests/fixtures/sample_callback_not_found.py"

    def test_invoke_callback_with_valid_callback(self):
        callback = f"python {self.callback_file}"
        callback_params = {"root": "project/root/path", "name": f"project_name_{uuid.uuid4()}"}
        expected_output = f"python callback called {callback_params}\n"
        expected_error = ""

        output, error = invoke_callback(callback, callback_params)
        self.assertEqual(output, expected_output)
        self.assertEqual(error, expected_error)

    def test_invoke_callback_with_invalid_callback(self):
        callback = f"python {self.callback_file_not_found}"
        callback_params = {"root": "project/root/path", "name": f"project_name_{uuid.uuid4()}"}
        expected_output = None
        expected_error = "No such file or directory"

        output, error = invoke_callback(callback, callback_params)
        self.assertEqual(output, expected_output)
        self.assertIn(expected_error, error)
