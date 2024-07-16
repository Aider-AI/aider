import unittest
from unittest.mock import patch
import sys
import io

from aider.commands import Commands
from aider.io import InputOutput


class TestScrape(unittest.TestCase):
    def setUp(self):
        self.io = InputOutput()
        self.commands = Commands(self.io, None)

    def test_cmd_web_imports_playwright(self):
        # Capture stdout to suppress output during the test
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            # Run the cmd_web command
            self.commands.cmd_web("https://example.com")

            # Try to import playwright
            try:
                import playwright
                playwright_imported = True
            except ImportError:
                playwright_imported = False

            # Assert that playwright was successfully imported
            self.assertTrue(
                playwright_imported,
                "Playwright should be importable after running cmd_web"
            )

            # Check if the content from example.com was scraped
            output = captured_output.getvalue()
            self.assertIn("This domain is for use in illustrative examples in documents.", output)

        finally:
            # Restore stdout
            sys.stdout = sys.__stdout__

if __name__ == "__main__":
    unittest.main()
