import os
import unittest
from unittest.mock import patch

from aider.io import InputOutput


class TestInputOutput(unittest.TestCase):
    def test_no_color_environment_variable(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            io = InputOutput()
            self.assertFalse(io.pretty)


if __name__ == "__main__":
    unittest.main()
